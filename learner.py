"""
learner.py — Self-improvement engine for Masnavi Transcription System

How it works
────────────
1. System transcribes a video → saves original TXT
2. Human opens DOCX in Word, fixes all mistakes, saves
3. Human uploads the corrected DOCX to the system
4. This module:
     a. Extracts clean text from the corrected DOCX
     b. Diffs it word-by-word against the original TXT
     c. Finds every (wrong → correct) pair automatically
     d. Saves all pairs to corrections.json
5. Every future transcription runs through all learned
   corrections before saving — automatically gets better

The system learns from WHOLE corrected files at once.
No need to manually list mistakes one by one.
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

CORRECTIONS_FILE = "corrections.json"

# ── Minimum phrase length to learn (avoid learning single noise chars) ──────
MIN_PHRASE_LEN  = 2   # characters
MAX_PHRASE_LEN  = 120 # characters — ignore very long replacements (paragraph shifts)
MIN_WORD_COUNT  = 1
MAX_WORD_COUNT  = 12  # max words in a correction phrase


# ════════════════════════════════════════════════════════════════════════════
# Corrections database
# ════════════════════════════════════════════════════════════════════════════

def load_corrections(path: str = CORRECTIONS_FILE) -> dict:
    """Load the corrections database from JSON."""
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Could not load corrections: {e}")
    return {
        "corrections": {},
        "stats": {
            "total_pairs_learned": 0,
            "episodes_learned_from": 0,
            "total_corrections_applied": 0,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
    }


def save_corrections(data: dict, path: str = CORRECTIONS_FILE):
    """Save corrections database atomically."""
    data["stats"]["last_updated"] = datetime.now().isoformat()
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(Path(path))


# ════════════════════════════════════════════════════════════════════════════
# Text extraction
# ════════════════════════════════════════════════════════════════════════════

def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract plain text from a corrected DOCX file.
    Strips all formatting — just the words.
    """
    try:
        from docx import Document
        doc = Document(docx_path)
        lines = []
        for para in doc.paragraphs:
            t = para.text.strip()
            if t:
                lines.append(t)
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Could not read DOCX: {e}")
        return ""


def extract_text_from_txt(txt_path: str) -> str:
    """Read original TXT, strip the structured header."""
    try:
        content = Path(txt_path).read_text(encoding="utf-8")
        # Remove the header block (lines starting with = or عنوان/تاریخ/ماخذ)
        lines = []
        header_done = False
        for line in content.splitlines():
            if not header_done:
                if line.startswith("=") or any(
                    line.startswith(k) for k in ["عنوان", "تاریخ", "ماخذ"]
                ):
                    continue
                else:
                    header_done = True
            if line.strip():
                lines.append(line.strip())
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Could not read TXT: {e}")
        return ""


# ════════════════════════════════════════════════════════════════════════════
# Core diff engine
# ════════════════════════════════════════════════════════════════════════════

def _tokenize(text: str) -> list:
    """
    Split text into tokens for diffing.
    Keeps punctuation attached to words to preserve Urdu/Arabic structure.
    Splits on whitespace only — does NOT split Arabic script on punctuation
    because Urdu words can contain ، and ۔ as part of their flow.
    """
    return text.split()


def _is_valid_pair(wrong: str, correct: str) -> bool:
    """
    Filter out noise pairs — only learn meaningful corrections.
    """
    wrong   = wrong.strip()
    correct = correct.strip()

    # Must actually be different
    if wrong == correct:
        return False

    # Both must have content
    if not wrong or not correct:
        return False

    # Length limits
    if len(wrong) < MIN_PHRASE_LEN or len(correct) < MIN_PHRASE_LEN:
        return False
    if len(wrong) > MAX_PHRASE_LEN or len(correct) > MAX_PHRASE_LEN:
        return False

    # Word count limits
    ww = len(wrong.split())
    cw = len(correct.split())
    if ww > MAX_WORD_COUNT or cw > MAX_WORD_COUNT:
        return False

    # At least one side must contain Urdu/Arabic/Persian or English letters
    # (filter out pure punctuation / number changes that are likely errors)
    has_letters = re.search(
        r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\w]',
        wrong + correct
    )
    if not has_letters:
        return False

    return True


def diff_and_learn(
    original_text: str,
    corrected_text: str,
    corrections_path: str = CORRECTIONS_FILE,
    episode_name: str = "",
) -> dict:
    """
    Core learning function.

    Compares original Whisper output against human-corrected text.
    Finds all differences automatically.
    Saves every (wrong → correct) pair to the corrections database.

    Returns summary dict with counts of what was learned.
    """
    orig_tokens = _tokenize(original_text)
    corr_tokens = _tokenize(corrected_text)

    if not orig_tokens or not corr_tokens:
        return {"new_pairs": 0, "updated_pairs": 0, "skipped": 0, "error": "Empty text"}

    # ── Run sequence diff ────────────────────────────────────────────────
    matcher = SequenceMatcher(
        None, orig_tokens, corr_tokens,
        autojunk=False  # important: don't skip common Urdu words as "junk"
    )
    opcodes = matcher.get_opcodes()

    # ── Extract replacement pairs ────────────────────────────────────────
    raw_pairs = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "replace":
            wrong   = " ".join(orig_tokens[i1:i2])
            correct = " ".join(corr_tokens[j1:j2])
            if _is_valid_pair(wrong, correct):
                raw_pairs.append((wrong, correct))
        # "delete" = word existed in original but removed in correction
        elif tag == "delete":
            wrong   = " ".join(orig_tokens[i1:i2])
            correct = ""
            if wrong.strip() and len(wrong) <= MAX_PHRASE_LEN:
                # Only learn deletions of short noise phrases
                if len(orig_tokens[i1:i2]) <= 3:
                    raw_pairs.append((wrong, correct))
        # "insert" = word added in correction that wasn't in original
        # These are harder to learn — skip for now

    # ── Merge consecutive small pairs into phrase-level corrections ──────
    # e.g. ("kya", "کیا") + ("hai", "ہے") → ("kya hai", "کیا ہے")
    merged = _merge_adjacent_pairs(opcodes, orig_tokens, corr_tokens)
    all_pairs = list(set(raw_pairs + merged))

    # ── Save to database ─────────────────────────────────────────────────
    data = load_corrections(corrections_path)
    corrections = data["corrections"]

    new_count     = 0
    updated_count = 0
    skipped_count = 0

    for wrong, correct in all_pairs:
        if not _is_valid_pair(wrong, correct) and not (wrong and not correct):
            skipped_count += 1
            continue

        if wrong in corrections:
            # Already known — increment frequency count
            corrections[wrong]["count"] += 1
            corrections[wrong]["correct"] = correct  # update if human changed again
            corrections[wrong]["last_seen"] = datetime.now().isoformat()
            if episode_name and episode_name not in corrections[wrong].get("episodes", []):
                corrections[wrong].setdefault("episodes", []).append(episode_name)
            updated_count += 1
        else:
            # New correction — add it
            corrections[wrong] = {
                "correct": correct,
                "count": 1,
                "added": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "episodes": [episode_name] if episode_name else [],
            }
            new_count += 1

    data["corrections"] = corrections
    data["stats"]["total_pairs_learned"] = len(corrections)
    data["stats"]["episodes_learned_from"] += 1
    save_corrections(data, corrections_path)

    logger.info(
        f"Learned from '{episode_name}': "
        f"{new_count} new, {updated_count} reinforced, {skipped_count} skipped. "
        f"Total in DB: {len(corrections)}"
    )

    return {
        "new_pairs":     new_count,
        "updated_pairs": updated_count,
        "skipped":       skipped_count,
        "total_in_db":   len(corrections),
        "episode":       episode_name,
    }


def _merge_adjacent_pairs(opcodes, orig_tokens, corr_tokens) -> list:
    """
    Find consecutive replace blocks that are close together and
    merge them into phrase-level corrections.

    Example:
      ("kya", "کیا") at pos 5  +  ("hai", "ہے") at pos 6
      → ("kya hai", "کیا ہے")
    This gives Whisper better phrase-level context for future fixes.
    """
    replaces = [
        (i1, i2, j1, j2)
        for tag, i1, i2, j1, j2 in opcodes
        if tag == "replace"
    ]
    merged = []
    i = 0
    while i < len(replaces):
        i1, i2, j1, j2 = replaces[i]
        # Look ahead: if next replace is within 2 tokens, merge
        j = i + 1
        while j < len(replaces):
            ni1, ni2, nj1, nj2 = replaces[j]
            gap_orig = ni1 - i2
            gap_corr = nj1 - j2
            if gap_orig <= 2 and gap_corr <= 2 and (i2 - i1 + ni2 - ni1) <= MAX_WORD_COUNT:
                # Extend merge window
                i2, j2 = ni2, nj2
                j += 1
            else:
                break
        if j > i + 1:
            wrong   = " ".join(orig_tokens[i1:i2])
            correct = " ".join(corr_tokens[j1:j2])
            if _is_valid_pair(wrong, correct):
                merged.append((wrong, correct))
        i = j if j > i + 1 else i + 1
    return merged


# ════════════════════════════════════════════════════════════════════════════
# Apply corrections to new transcripts
# ════════════════════════════════════════════════════════════════════════════

def apply_corrections(text: str, corrections_path: str = CORRECTIONS_FILE) -> tuple:
    """
    Apply all learned corrections to a new transcript.

    Corrections are applied in order of frequency (most-seen first)
    so the most reliable fixes run before less certain ones.

    Returns (corrected_text, count_applied).
    """
    data = load_corrections(corrections_path)
    corrections = data.get("corrections", {})

    if not corrections:
        return text, 0

    # Sort by frequency — most reinforced corrections applied first
    sorted_corrections = sorted(
        corrections.items(),
        key=lambda x: x[1].get("count", 1),
        reverse=True
    )

    applied = 0
    for wrong, info in sorted_corrections:
        correct = info.get("correct", "")
        if wrong in text:
            text = text.replace(wrong, correct)
            applied += 1

    # Update stats
    if applied > 0:
        data["stats"]["total_corrections_applied"] = (
            data["stats"].get("total_corrections_applied", 0) + applied
        )
        save_corrections(data, corrections_path)

    if applied:
        logger.info(f"Auto-applied {applied} corrections from database.")

    return text, applied


# ════════════════════════════════════════════════════════════════════════════
# Convenience: learn from a file pair
# ════════════════════════════════════════════════════════════════════════════

def learn_from_files(
    original_txt_path: str,
    corrected_docx_path: str,
    corrections_path: str = CORRECTIONS_FILE,
) -> dict:
    """
    High-level function: give it the original TXT and corrected DOCX,
    it does everything automatically.

    Returns summary of what was learned.
    """
    episode_name = Path(corrected_docx_path).stem

    logger.info(f"Extracting original text from: {original_txt_path}")
    original_text = extract_text_from_txt(original_txt_path)

    logger.info(f"Extracting corrected text from: {corrected_docx_path}")
    corrected_text = extract_text_from_docx(corrected_docx_path)

    if not original_text:
        return {"error": f"Could not read original TXT: {original_txt_path}"}
    if not corrected_text:
        return {"error": f"Could not read corrected DOCX: {corrected_docx_path}"}

    logger.info(f"Diffing {len(original_text.split())} words vs {len(corrected_text.split())} words…")
    return diff_and_learn(original_text, corrected_text, corrections_path, episode_name)


def get_stats(corrections_path: str = CORRECTIONS_FILE) -> dict:
    """Return current database statistics for display."""
    data = load_corrections(corrections_path)
    corrections = data.get("corrections", {})
    stats = data.get("stats", {})

    if not corrections:
        return {**stats, "top_corrections": [], "total_pairs": 0}

    # Top 10 most frequent corrections
    top = sorted(corrections.items(), key=lambda x: x[1].get("count",1), reverse=True)[:10]
    top_list = [
        {"wrong": k, "correct": v["correct"], "count": v["count"]}
        for k, v in top
    ]

    return {
        **stats,
        "total_pairs": len(corrections),
        "top_corrections": top_list,
    }
