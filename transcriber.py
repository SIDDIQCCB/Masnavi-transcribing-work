"""
Core transcription engine for Masnavi lectures.
Handles audio download, transcription, and text normalization.
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Arabic / Urdu normalisation map
# ---------------------------------------------------------------------------
NORMALISATION_MAP = {
    # Arabic forms → Urdu/Persian preferred forms
    "ك": "ک",   # Arabic kaf  → Urdu kaf
    "ي": "ی",   # Arabic yeh  → Urdu yeh
    "ة": "ۃ",   # Arabic taa marbuta
    "ى": "ی",   # Arabic alef maqsura
    # Allah – Arabic → Urdu
    "الله": "اللہ",
    "اللہ": "اللہ",   # already correct, keep
    # Common diacritics that clutter printed text
    "\u064b": "",  # tanwin fath
    "\u064c": "",  # tanwin damm
    "\u064d": "",  # tanwin kasr
    "\u0640": "",  # tatweel / kashida (stretch character)
}

# Compile a single regex for all multi-char keys (longest first)
_MULTI = {k: v for k, v in NORMALISATION_MAP.items() if len(k) > 1}
_SINGLE = {k: v for k, v in NORMALISATION_MAP.items() if len(k) == 1}
_MULTI_RE = re.compile("|".join(re.escape(k) for k in sorted(_MULTI, key=len, reverse=True)))


def normalise_text(text: str) -> str:
    """Apply Arabic→Urdu normalisation to a transcript string."""
    text = _MULTI_RE.sub(lambda m: _MULTI[m.group(0)], text)
    text = text.translate(str.maketrans(_SINGLE))
    return text


def clean_transcript(text: str) -> str:
    """
    Post-process raw Whisper output:
    - Remove repeated filler lines
    - Ensure proper line breaks between segments
    - Remove Whisper artefacts like [MUSIC], [Applause] etc.
    - Add Unicode RTL markers so Urdu/Persian text displays right-to-left
    """
    # Unicode bidi control characters
    RLM  = "\u200f"   # Right-to-Left Mark  — signals RTL context
    RLE  = "\u202b"   # Right-to-Left Embedding — opens RTL block
    PDF  = "\u202c"   # Pop Directional Formatting — closes RLE/LRE

    # Remove common artefact tags
    text = re.sub(r"\[.*?\]", "", text)
    # Collapse 3+ newlines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]

    # Remove duplicate consecutive lines
    cleaned = []
    prev = None
    for line in lines:
        if line != prev:
            if line.strip():
                # Wrap non-empty lines: RLE…text…PDF + trailing RLM
                # This forces every line to be displayed RTL in any
                # Unicode-aware viewer, Word, Notepad, LibreOffice, etc.
                line = f"{RLE}{line.strip()}{PDF}{RLM}"
            cleaned.append(line)
        prev = line

    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# Audio download
# ---------------------------------------------------------------------------

def download_audio(url: str, output_dir: str, progress_cb: Optional[Callable] = None) -> Optional[str]:
    """
    Download audio from a YouTube URL using yt-dlp.
    Returns path to downloaded audio file or None on failure.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed. Run: pip install yt-dlp")
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "%(id)s.%(ext)s")

    def _hook(d):
        if progress_cb and d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                pct = downloaded / total * 100
                progress_cb("downloading", pct)
        elif progress_cb and d.get("status") == "finished":
            progress_cb("downloading", 100)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "progress_hooks": [_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id", "unknown")
            title = info.get("title", video_id)
            audio_path = output_dir / f"{video_id}.mp3"
            if audio_path.exists():
                return str(audio_path), title
            # Fallback: find any mp3 with matching id
            for f in output_dir.glob(f"{video_id}*"):
                if f.suffix in (".mp3", ".m4a", ".webm", ".opus"):
                    return str(f), title
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
    return None, None


def get_video_title(url: str) -> Optional[str]:
    """Fetch video title without downloading."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title")
    except Exception:
        return None


def get_playlist_videos(playlist_url: str) -> list:
    """
    Return list of dicts: {id, url, title} for every video in a playlist.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed.")
        return []

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries = info.get("entries", [])
            result = []
            for entry in entries:
                vid_id = entry.get("id", "")
                result.append({
                    "id": vid_id,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "title": entry.get("title", vid_id),
                })
            return result
    except Exception as e:
        logger.error(f"Could not fetch playlist: {e}")
        return []


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def _auto_cpu_threads() -> int:
    """Detect available CPU cores and return safe thread count."""
    import os
    cores = os.cpu_count() or 2
    # Leave 1 core free for OS + other tasks on minimum-spec machines
    return max(1, cores - 1)


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,       # None = auto-detect per segment
    model_size: str = "small",            # 'small' is best for minimum-spec CPUs
    progress_cb: Optional[Callable] = None,
    device: str = "cpu",
    compute_type: str = "int8",
    cpu_threads: Optional[int] = None,    # None = auto-detect from CPU cores
) -> Optional[str]:
    """
    Transcribe mixed Urdu + Persian + English audio using faster-whisper.

    MULTILINGUAL (Urdu + Persian + English in same video)
    ─────────────────────────────────────────────────────
    • language=None  — Do NOT lock to one language. Whisper detects each
                       segment automatically. English lines stay in English
                       script, Urdu lines in Nastaliq, Persian lines in
                       Nastaliq. Forcing language="ur" causes English words
                       to be written in wrong Urdu phonetics.
    • initial_prompt — A bilingual seed telling Whisper this is a Masnavi
                       lecture mixing Urdu, Persian, and some English. This
                       guides the model without locking it to one script.

    MINIMUM-SPEC CPU OPTIMISATION
    ──────────────────────────────
    • model='small'  — 465 MB RAM, ~2x faster than medium, still good for
                       Urdu/Persian. Use 'medium' if you have 8 GB+ RAM.
    • cpu_threads    — Auto-detected from machine cores (leaves 1 free for OS).
    • int8 compute   — 4x faster than float32, same quality.
    • beam_size=3    — Reduced from 5. Saves ~30% time with minimal accuracy
                       loss. Use beam_size=5 on faster machines.
    • chunk_length=25 — Shorter chunks = less RAM used at a time.
    • num_workers=1  — Safe for minimum-spec (2 on better machines).

    Returns full transcript string or None on error.
    """
    import os as _os
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("faster-whisper not installed. Run: pip install faster-whisper")
        return None

    # Auto-detect threads if not specified
    threads = cpu_threads if cpu_threads is not None else _auto_cpu_threads()

    # Choose num_workers based on available RAM (conservative default)
    ram_gb = 4  # assume minimum spec; override not needed
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / 1_073_741_824
    except ImportError:
        pass
    num_workers = 2 if ram_gb >= 8 else 1

    if progress_cb:
        progress_cb("loading_model", 0)

    logger.info(f"Loading Whisper '{model_size}' | threads={threads} | workers={num_workers} | RAM≈{ram_gb:.1f}GB")
    try:
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=threads,
            num_workers=num_workers,
        )
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        return None

    if progress_cb:
        progress_cb("transcribing", 0)

    # ── Initial prompt: use vocabulary built from 72 corrected episodes ──
    # If batch_learn.py has been run, this prompt contains hundreds of
    # correct terms from YOUR specific lectures — dramatically better.
    # Falls back to a basic prompt if vocabulary hasn't been built yet.
    try:
        from batch_learn import get_enhanced_prompt
        INITIAL_PROMPT = get_enhanced_prompt()
        logger.info("Using enhanced prompt from vocabulary database.")
    except Exception:
        INITIAL_PROMPT = (
            "یہ مثنوی مولانا روم کا اردو درس ہے۔ "
            "اس میں فارسی اشعار اور انگریزی الفاظ بھی ہیں۔ "
            "بسم اللہ الرحمٰن الرحیم۔ اللہ، رسول، قرآن، حدیث، مثنوی، مولانا رومی۔"
            "Allah, Rumi, Masnavi, volume, episode."
        )

    logger.info(f"Transcribing (multilingual: Urdu+Persian+English)…")
    try:
        import subprocess, json as _json
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
            capture_output=True, text=True
        )
        total_duration = 1.0
        if probe.returncode == 0:
            fmt = _json.loads(probe.stdout).get("format", {})
            total_duration = float(fmt.get("duration", 1.0))

        segments, info = model.transcribe(
            audio_path,
            language=language,                     # ← None = auto per segment
            task="transcribe",
            initial_prompt=INITIAL_PROMPT,
            beam_size=3,                           # ← min-spec: 3 instead of 5
            temperature=0,
            condition_on_previous_text=True,
            repetition_penalty=1.1,
            chunk_length=25,                       # ← min-spec: shorter chunks
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 400,
                "speech_pad_ms": 200,
            },
            word_timestamps=False,
        )

        lines = []
        for seg in segments:
            lines.append(seg.text.strip())
            if progress_cb and total_duration:
                pct = min(seg.end / total_duration * 100, 99)
                progress_cb("transcribing", pct)

        if progress_cb:
            progress_cb("transcribing", 100)

        raw = "\n".join(lines)
        normalised = normalise_text(raw)
        cleaned = clean_transcript(normalised)

        # ── Pass 1: Apply learned corrections (wrong→correct pairs) ─────
        try:
            from learner import apply_corrections
            cleaned, n_applied = apply_corrections(cleaned)
            if n_applied:
                logger.info(f"Self-improvement: applied {n_applied} learned corrections.")
        except Exception as e:
            logger.warning(f"Could not apply corrections (non-fatal): {e}")

        # ── Pass 2: Fuzzy vocabulary fix from 72-episode database ────────
        # Fixes words that are CLOSE to known correct words from your lectures
        try:
            from batch_learn import apply_fuzzy_corrections
            cleaned, n_fuzzy = apply_fuzzy_corrections(cleaned)
            if n_fuzzy:
                logger.info(f"Vocabulary fix: corrected {n_fuzzy} words using lecture database.")
        except Exception:
            pass  # vocabulary DB not built yet — silently skip

        return cleaned

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def safe_filename(title: str) -> str:
    """Convert a video title to a safe filename."""
    # Keep Urdu/Arabic/Persian characters plus ASCII word chars
    title = re.sub(r'[<>:"/\\|?*]', "", title)
    title = title.strip().replace(" ", "_")
    return title[:200] or "untitled"




def _make_docx(title: str, clean_lines: list, date_str: str, docx_path) -> bool:
    """
    Create a fully editable DOCX using python-docx (pure Python, no Node.js).
    RTL Urdu text, Jameel Noori Nastaleeq font, justified alignment.
    Returns True on success.
    """
    import re as _re
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    URDU_FONT  = "Jameel Noori Nastaleeq"
    LATIN_FONT = "Calibri"
    RTL_RE     = _re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

    def is_verse(line):
        """Short line with mostly Arabic/Urdu chars = Quran or Persian verse."""
        if len(line) >= 130: return False
        rtl = len(RTL_RE.findall(line))
        total = len(line.replace(" ",""))
        return total > 0 and (rtl / total) > 0.85 and len(line) < 120

    def set_rtl_para(para):
        """Set paragraph-level RTL and bidirectional."""
        pPr = para._p.get_or_add_pPr()
        bidi = OxmlElement("w:bidi")
        bidi.set(qn("w:val"), "1")
        pPr.insert(0, bidi)

    def set_rtl_run(run):
        """Set run-level RTL."""
        rPr = run._r.get_or_add_rPr()
        rtl = OxmlElement("w:rtl")
        rtl.set(qn("w:val"), "1")
        rPr.append(rtl)

    def add_shading(para, fill_hex):
        """Add background shading to paragraph."""
        pPr = para._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  fill_hex)
        pPr.append(shd)

    def add_border_right(para, color="B8860B", size=18):
        """Add right border (visual marker for verse lines)."""
        pPr  = para._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        right = OxmlElement("w:right")
        right.set(qn("w:val"),   "single")
        right.set(qn("w:sz"),    str(size))
        right.set(qn("w:space"), "6")
        right.set(qn("w:color"), color)
        pBdr.append(right)
        pPr.append(pBdr)

    try:
        doc = Document()

        # ── Page setup: A4, 1-inch margins ──────────────────────────────
        section = doc.sections[0]
        section.page_width   = Inches(8.27)
        section.page_height  = Inches(11.69)
        section.left_margin  = section.right_margin  = Inches(1.0)
        section.top_margin   = section.bottom_margin = Inches(1.0)

        # ── Document-level RTL default ───────────────────────────────────
        settings = doc.settings.element
        docDefaults = OxmlElement("w:docDefaults")
        rPrDefault  = OxmlElement("w:rPrDefault")
        rPr_def     = OxmlElement("w:rPr")
        rtl_def     = OxmlElement("w:rtl")
        rtl_def.set(qn("w:val"), "1")
        rPr_def.append(rtl_def)
        rPrDefault.append(rPr_def)
        docDefaults.append(rPrDefault)

        # ── Title paragraph ──────────────────────────────────────────────
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_rtl_para(title_para)
        add_shading(title_para, "1A1409")
        title_para.paragraph_format.space_before = Pt(0)
        title_para.paragraph_format.space_after  = Pt(6)
        title_para.paragraph_format.line_spacing = Pt(36)
        run = title_para.add_run(title)
        run.font.name = URDU_FONT
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xF0, 0xD0, 0x80)
        set_rtl_run(run)

        # Date line
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para.paragraph_format.space_after = Pt(12)
        dr = date_para.add_run(date_str)
        dr.font.name = LATIN_FONT
        dr.font.size = Pt(9)
        dr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

        # Ornament
        orn_para = doc.add_paragraph()
        orn_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        orn_para.paragraph_format.space_after = Pt(14)
        or2 = orn_para.add_run("✦   ✦   ✦")
        or2.font.name  = LATIN_FONT
        or2.font.size  = Pt(13)
        or2.font.color.rgb = RGBColor(0xB8, 0x86, 0x0B)

        # ── Content paragraphs ────────────────────────────────────────────
        for line in clean_lines:
            verse = is_verse(line)
            para  = doc.add_paragraph()
            set_rtl_para(para)
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

            para.paragraph_format.space_before  = Pt(3)
            para.paragraph_format.space_after   = Pt(3)
            para.paragraph_format.line_spacing  = Pt(28) if verse else Pt(32)

            if verse:
                add_shading(para, "FDF6E0")
                add_border_right(para)
                para.paragraph_format.left_indent  = Inches(0.3)
                para.paragraph_format.right_indent = Inches(0.2)

            run = para.add_run(line)
            run.font.name = URDU_FONT
            run.font.size = Pt(15) if verse else Pt(13)
            run.font.color.rgb = RGBColor(0x4A, 0x2C, 0x00) if verse else RGBColor(0x1A, 0x14, 0x09)
            set_rtl_run(run)

        # Footer note
        footer_para = doc.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.paragraph_format.space_before = Pt(18)
        fr = footer_para.add_run(f"Masnavi Lecture Transcription System  |  {date_str}")
        fr.font.name  = LATIN_FONT
        fr.font.size  = Pt(8)
        fr.font.color.rgb = RGBColor(0xA0, 0x80, 0x40)

        doc.save(str(docx_path))
        return True

    except Exception as e:
        logger.error(f"python-docx error: {e}")
        return False


def save_transcript(title: str, text: str, output_dir: str = "transcripts") -> str:
    """
    Save transcript as two files:
      1. <title>.docx  — Editable in Microsoft Word, beautiful Nastaliq font
      2. <title>.txt   — Clean text for future chatbot/database

    Uses python-docx (pure Python) — no Node.js required.
    """
    BIDI = str.maketrans("", "", "\u200f\u202b\u202c\u202a\u202d\u202e")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    date_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    base_name = safe_filename(title)

    # Clean lines shared by both outputs
    clean_lines = []
    for line in text.splitlines():
        line = line.translate(BIDI).strip()
        if line:
            clean_lines.append(line)

    # ── FILE 1: TXT for database/chatbot ─────────────────────────────────
    txt_path = out / (base_name + ".txt")
    header = "\n".join([
        "=" * 60,
        f"عنوان     : {title}",
        f"تاریخ     : {date_str}",
        f"ماخذ      : Masnavi Lecture Transcription System",
        "=" * 60, "",
    ])
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(clean_lines))
    logger.info(f"Saved TXT: {txt_path}")

    # ── FILE 2: DOCX for editing/printing ────────────────────────────────
    docx_path = out / (base_name + ".docx")
    ok = _make_docx(title, clean_lines, date_str, docx_path)
    if ok:
        logger.info(f"Saved DOCX: {docx_path}")
    else:
        logger.warning("DOCX creation failed — TXT still saved.")

    return str(docx_path) if ok else str(txt_path)
