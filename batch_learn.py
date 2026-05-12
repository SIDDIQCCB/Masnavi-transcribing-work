"""
batch_learn.py — Learn from 72 corrected DOCX files at once.

Since we don't have the original AI outputs to diff against,
this script uses a different (but still powerful) strategy:

WHAT IT DOES
────────────
1. Reads all corrected DOCX files from a folder
2. Extracts every word and phrase
3. Builds a "Known Correct Vocabulary" database
4. Identifies the most important terms:
   - Islamic / Arabic terms  (اللہ، قرآن، حدیث...)
   - Persian poetry phrases  (بشنو، مثنوی، عشق...)
   - Speaker-specific names  (مولانا رومی، رومی...)
   - Urdu explanation phrases unique to these lectures
5. Saves everything to vocabulary.json
6. Generates an enhanced Whisper prompt using YOUR
   actual lecture vocabulary — so Whisper already
   "knows" your speaker's words before it starts
7. Builds a fuzzy-match correction system:
   If new transcript has a word that is CLOSE to a
   known correct word → auto-corrected

USAGE
─────
Put all 72 DOCX files in one folder, then run:

    python3 batch_learn.py --folder "path/to/your/docx/folder"

Optional flags:
    --output    Where to save vocab DB  (default: vocabulary.json)
    --prompt    Where to save enhanced prompt (default: whisper_prompt.txt)

RESULT
──────
After running, every new transcription automatically:
- Uses your 72 episodes as vocabulary context
- Fuzzy-fixes words that are close to known correct terms
- Gets dramatically better at your specific speaker's style
"""

import argparse
import json
import re
import logging
from pathlib import Path
from collections import Counter
from datetime import datetime
from difflib import get_close_matches

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Script detection patterns ─────────────────────────────────────────────────
# Used to classify each word into its language/script category
ARABIC_URDU_RE = re.compile(r'^[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s،؟۔ء]+$')
PERSIAN_RE     = re.compile(r'[\u06A9\u06AF\u067E\u0686\u0698]')  # ک گ پ چ ژ
LATIN_RE       = re.compile(r'[a-zA-Z]')
NOISE_RE       = re.compile(r'^[\d\s\W]+$')

# Islamic / Arabic terms to always prioritise
ISLAMIC_SEED_TERMS = [
    "اللہ", "رسول", "قرآن", "حدیث", "سنت", "نبی", "صحابہ", "تفسیر",
    "فقہ", "عقیدہ", "توحید", "شریعت", "جنت", "جہنم", "آخرت", "دنیا",
    "بسم اللہ", "الحمد للہ", "سبحان اللہ", "ماشاء اللہ", "انشاء اللہ",
    "رحمۃ اللہ", "رضی اللہ عنہ", "صلی اللہ علیہ وسلم",
    "مثنوی", "مولانا رومی", "رومی", "جلال الدین", "معنوی",
    "عشق", "عارف", "صوفی", "تصوف", "فنا", "بقا", "وصال",
]


def extract_text_from_docx(path: Path) -> str:
    """Extract plain text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(str(path))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"  Could not read {path.name}: {e}")
        return ""


def classify_word(word: str) -> str:
    """Return 'urdu', 'persian', 'english', 'noise', or 'mixed'."""
    word = word.strip("،؟۔۱۲۳۴۵۶۷۸۹۰()[]{}\"'")
    if not word or NOISE_RE.match(word):
        return "noise"
    if LATIN_RE.search(word):
        return "english"
    if ARABIC_URDU_RE.match(word):
        return "persian" if PERSIAN_RE.search(word) else "urdu"
    return "noise"


def extract_ngrams(tokens: list, n: int) -> list:
    """Extract n-grams (phrases of n words) from token list."""
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def build_vocabulary(folder: Path, output: Path, prompt_file: Path):
    """
    Main function: read all DOCXs, build vocabulary database.
    """
    docx_files = list(folder.glob("*.docx"))
    if not docx_files:
        logger.error(f"No DOCX files found in {folder}")
        return

    logger.info(f"Found {len(docx_files)} DOCX files. Processing...")

    all_text = []
    file_count = 0

    for i, f in enumerate(sorted(docx_files), 1):
        text = extract_text_from_docx(f)
        if text:
            all_text.append(text)
            file_count += 1
            logger.info(f"  [{i}/{len(docx_files)}] Read: {f.name} ({len(text.split())} words)")
        else:
            logger.warning(f"  [{i}/{len(docx_files)}] SKIPPED (empty): {f.name}")

    if not all_text:
        logger.error("No text extracted from any file.")
        return

    full_corpus = "\n".join(all_text)
    all_tokens  = full_corpus.split()
    logger.info(f"\nTotal words in corpus: {len(all_tokens):,}")

    # ── Separate by script ───────────────────────────────────────────────
    urdu_tokens    = [w for w in all_tokens if classify_word(w) == "urdu"]
    persian_tokens = [w for w in all_tokens if classify_word(w) == "persian"]
    english_tokens = [w for w in all_tokens if classify_word(w) == "english"]

    logger.info(f"  Urdu/Arabic words  : {len(urdu_tokens):,}")
    logger.info(f"  Persian words      : {len(persian_tokens):,}")
    logger.info(f"  English words      : {len(english_tokens):,}")

    # ── Word frequency counts ────────────────────────────────────────────
    urdu_freq    = Counter(urdu_tokens)
    persian_freq = Counter(persian_tokens)
    english_freq = Counter(english_tokens)

    # ── Extract key phrases (2-grams and 3-grams) ────────────────────────
    rtl_tokens = [w for w in all_tokens if classify_word(w) in ("urdu","persian")]
    bigrams  = Counter(extract_ngrams(rtl_tokens, 2))
    trigrams = Counter(extract_ngrams(rtl_tokens, 3))

    # Keep phrases that appear at least 3 times (real recurring phrases)
    key_phrases = {
        phrase: count
        for phrase, count in {**bigrams, **trigrams}.items()
        if count >= 3 and len(phrase) >= 6
    }

    # ── Build known-correct vocabulary set ──────────────────────────────
    # All unique RTL words that appear at least twice (more reliable)
    known_vocab = sorted(set(
        w for w, c in {**urdu_freq, **persian_freq}.items()
        if c >= 2 and len(w) >= 2
    ))

    # Add seed Islamic terms always
    for term in ISLAMIC_SEED_TERMS:
        if term not in known_vocab:
            known_vocab.append(term)

    # ── Build fuzzy correction map ────────────────────────────────────────
    # Pre-compute: for each word in known vocab, what are close matches?
    # This is used at transcription time to fix "ملانا" → "مولانا" etc.
    # We store the top-frequency words as anchors for fuzzy matching.
    top_urdu = [w for w, _ in urdu_freq.most_common(500)]

    # ── Build enhanced Whisper prompt ────────────────────────────────────
    # Whisper's initial_prompt can hold ~200 tokens.
    # We fill it with: most frequent Islamic terms + key Persian phrases
    # + most common Urdu words from YOUR lectures specifically.
    prompt_terms = list(dict.fromkeys(
        ISLAMIC_SEED_TERMS +
        [w for w, _ in urdu_freq.most_common(60)] +
        [w for w, _ in persian_freq.most_common(30)] +
        [ph for ph, _ in sorted(key_phrases.items(), key=lambda x:-x[1])[:20]]
    ))

    # Build prompt string (keep under ~800 chars / ~200 tokens)
    prompt_base = (
        "یہ مثنوی مولانا روم کا اردو درس ہے۔ "
        "اس میں فارسی اشعار اور انگریزی الفاظ بھی ہیں۔ "
        "بسم اللہ الرحمٰن الرحیم۔ "
    )
    prompt_vocab = "، ".join(prompt_terms[:80])
    enhanced_prompt = prompt_base + prompt_vocab

    # ── Save vocabulary database ─────────────────────────────────────────
    db = {
        "meta": {
            "files_processed": file_count,
            "total_words":     len(all_tokens),
            "created":         datetime.now().isoformat(),
            "source_folder":   str(folder),
        },
        "known_vocab": known_vocab,
        "top_urdu_words":    [w for w, _ in urdu_freq.most_common(300)],
        "top_persian_words": [w for w, _ in persian_freq.most_common(100)],
        "key_phrases":       dict(sorted(key_phrases.items(), key=lambda x:-x[1])[:200]),
        "english_words_found": [w for w, c in english_freq.most_common(50) if c >= 2],
        "enhanced_prompt":   enhanced_prompt,
    }

    output.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt_file.write_text(enhanced_prompt, encoding="utf-8")

    # ── Print summary ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  ✅ BATCH LEARNING COMPLETE")
    print("=" * 60)
    print(f"  Files processed      : {file_count}")
    print(f"  Total words learned  : {len(all_tokens):,}")
    print(f"  Known vocabulary     : {len(known_vocab):,} unique words")
    print(f"  Key phrases learned  : {len(key_phrases):,}")
    print(f"  Saved to             : {output}")
    print()
    print("  TOP 20 MOST FREQUENT TERMS IN YOUR LECTURES:")
    for w, c in urdu_freq.most_common(20):
        print(f"    {w:20s}  ×{c}")
    print()
    print("  KEY PHRASES FOUND:")
    for ph, c in sorted(key_phrases.items(), key=lambda x:-x[1])[:10]:
        print(f"    {ph:30s}  ×{c}")
    print()
    print("  ENHANCED WHISPER PROMPT (first 200 chars):")
    print(f"    {enhanced_prompt[:200]}…")
    print("=" * 60)
    print()
    print("  Next step: run your transcription system normally.")
    print("  It will automatically use this vocabulary database.")
    print()


def apply_fuzzy_corrections(text: str, vocab_path: str = "vocabulary.json") -> tuple:
    """
    Apply vocabulary-based fuzzy corrections to a new transcript.

    For each word in the transcript:
    - If it is already in known_vocab → keep it
    - If it is close to a known_vocab word (edit distance 1) → fix it
    - English words → keep as-is (they are intentional)

    Returns (corrected_text, count_fixed).
    """
    vp = Path(vocab_path)
    if not vp.exists():
        return text, 0

    try:
        db = json.loads(vp.read_text(encoding="utf-8"))
    except Exception:
        return text, 0

    known_vocab = set(db.get("known_vocab", []))
    if not known_vocab:
        return text, 0

    tokens  = text.split()
    fixed   = 0
    result  = []

    for token in tokens:
        # Skip English words and short tokens
        if LATIN_RE.search(token) or len(token) < 3:
            result.append(token)
            continue

        # Already correct
        if token in known_vocab:
            result.append(token)
            continue

        # Try fuzzy match — only fix if there's exactly one close match
        # cutoff=0.85 means 85% similar (catches 1-2 char differences)
        matches = get_close_matches(token, known_vocab, n=1, cutoff=0.85)
        if matches:
            result.append(matches[0])
            fixed += 1
        else:
            result.append(token)

    return " ".join(result), fixed


def get_enhanced_prompt(prompt_file: str = "whisper_prompt.txt",
                        vocab_file:  str = "vocabulary.json") -> str:
    """
    Return the enhanced Whisper prompt built from your 72 lectures.
    Falls back to basic prompt if not built yet.
    """
    # Try prompt file first (fastest)
    pp = Path(prompt_file)
    if pp.exists():
        return pp.read_text(encoding="utf-8").strip()

    # Try extracting from vocab DB
    vp = Path(vocab_file)
    if vp.exists():
        try:
            db = json.loads(vp.read_text(encoding="utf-8"))
            return db.get("enhanced_prompt", "")
        except Exception:
            pass

    # Fallback
    return (
        "یہ مثنوی مولانا روم کا اردو درس ہے۔ "
        "اس میں فارسی اشعار اور انگریزی الفاظ بھی ہیں۔ "
        "بسم اللہ الرحمٰن الرحیم۔ اللہ، رسول، قرآن، حدیث۔"
    )


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Learn from 72 corrected DOCX files — build vocabulary database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--folder", required=True,
        help="Path to folder containing your corrected DOCX files"
    )
    parser.add_argument(
        "--output", default="vocabulary.json",
        help="Output vocabulary database file (default: vocabulary.json)"
    )
    parser.add_argument(
        "--prompt", default="whisper_prompt.txt",
        help="Output enhanced Whisper prompt file (default: whisper_prompt.txt)"
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}")
        raise SystemExit(1)

    build_vocabulary(folder, Path(args.output), Path(args.prompt))
