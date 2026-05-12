"""
inp_to_docx.py — Batch convert corrupted InPage (.inp) files to Word DOCX

How it works:
    InPage .inp files store Urdu text internally in UTF-16 encoding.
    Even when the file is "corrupted" and InPage cannot open it,
    the actual Urdu text is still safely inside the raw bytes.
    This script reads those raw bytes directly and recovers everything.

Usage:
    # Convert all .inp files in a folder:
    python inp_to_docx.py --folder "C:\\Users\\You\\corrupted_files"

    # Convert a single file:
    python inp_to_docx.py --file "masnavi_part_71.inp"

    # Convert and save to a specific output folder:
    python inp_to_docx.py --folder "C:\\inp_files" --output "C:\\recovered_docx"

Output:
    One DOCX file per .inp file, saved in the output folder.
    Same filename, .docx extension.
    Opens directly in Microsoft Word with Nastaliq font + RTL formatting.
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


# ── Urdu/Arabic Unicode ranges ────────────────────────────────────────────────
URDU_RE   = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
VERSE_RE  = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


# ════════════════════════════════════════════════════════════════════════════════
# STEP 1 — Extract Urdu text from raw .inp bytes
# ════════════════════════════════════════════════════════════════════════════════

def extract_text_from_inp(filepath: str) -> str:
    """
    Read raw bytes from an InPage .inp file and extract all Urdu/Arabic text.

    InPage stores text in UTF-16 Little Endian encoding internally.
    We scan every 2-byte pair, decode as UTF-16-LE, and keep only
    characters that fall in Urdu/Arabic/Persian Unicode ranges.
    This works even on completely corrupted files.

    Returns extracted text as a clean string.
    """
    with open(filepath, "rb") as f:
        raw = f.read()

    chars = []
    i = 0
    while i < len(raw) - 1:
        try:
            char = raw[i:i+2].decode("utf-16-le")
            cp   = ord(char)

            # Keep Urdu/Arabic/Persian characters
            if (0x0600 <= cp <= 0x06FF or   # Arabic/Urdu main block
                0x0750 <= cp <= 0x077F or   # Arabic supplement
                0xFB50 <= cp <= 0xFDFF or   # Arabic presentation forms A
                0xFE70 <= cp <= 0xFEFF or   # Arabic presentation forms B
                cp == 0x0020 or             # Space
                cp == 0x060C or             # Urdu comma ،
                cp == 0x06D4 or             # Urdu full stop ۔
                cp == 0x061F or             # Arabic question mark ؟
                cp == 0x0021 or             # Exclamation !
                cp == 0x000A):              # Newline
                chars.append(char)
            else:
                # Non-Urdu character = word boundary
                if chars and chars[-1] != "\n":
                    chars.append("\n")
        except Exception:
            pass
        i += 2

    raw_text = "".join(chars)

    # ── Clean up extracted lines ──────────────────────────────────────────
    seen  = set()
    lines = []

    for line in raw_text.split("\n"):
        line = line.strip()

        # Keep only lines with meaningful Urdu content (3+ chars)
        if len(URDU_RE.findall(line)) < 3:
            continue

        # Remove exact duplicates (InPage stores some strings multiple times
        # internally for indexing — we only want each line once)
        if line in seen:
            continue

        seen.add(line)
        lines.append(line)

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# STEP 2 — Convert extracted text to DOCX
# ════════════════════════════════════════════════════════════════════════════════

def is_verse(line: str) -> bool:
    """
    Detect Persian/Arabic verse lines (short lines, mostly RTL characters).
    These get special formatting — cream background + gold right border.
    """
    if len(line) >= 130:
        return False
    rtl   = len(VERSE_RE.findall(line))
    total = len(line.replace(" ", ""))
    return total > 0 and (rtl / total) > 0.85 and len(line) < 120


def _set_rtl_para(para):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr  = para._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.insert(0, bidi)


def _set_rtl_run(run):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    rPr = run._r.get_or_add_rPr()
    rtl = OxmlElement("w:rtl")
    rtl.set(qn("w:val"), "1")
    rPr.append(rtl)


def _add_shading(para, fill_hex: str):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  fill_hex)
    pPr.append(shd)


def _add_border_right(para, color="B8860B", size=18):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr  = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    right = OxmlElement("w:right")
    right.set(qn("w:val"),   "single")
    right.set(qn("w:sz"),    str(size))
    right.set(qn("w:space"), "6")
    right.set(qn("w:color"), color)
    pBdr.append(right)
    pPr.append(pBdr)


def build_docx(title: str, lines: list, out_path: str) -> bool:
    """
    Build a properly formatted DOCX from a list of Urdu text lines.
    RTL direction, Jameel Noori Nastaleeq font, verse highlighting.
    Returns True on success.
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("ERROR: python-docx not installed.")
        print("Run: pip install python-docx")
        return False

    URDU_FONT  = "Jameel Noori Nastaleeq"
    LATIN_FONT = "Calibri"
    date_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    doc     = Document()
    section = doc.sections[0]
    section.page_width   = Inches(8.27)   # A4
    section.page_height  = Inches(11.69)
    section.left_margin  = section.right_margin  = Inches(1.0)
    section.top_margin   = section.bottom_margin = Inches(1.0)

    # ── Title block ──────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_rtl_para(tp)
    _add_shading(tp, "1A1409")
    tp.paragraph_format.space_before = Pt(0)
    tp.paragraph_format.space_after  = Pt(4)
    tp.paragraph_format.line_spacing = Pt(36)
    tr = tp.add_run(title)
    tr.font.name      = URDU_FONT
    tr.font.size      = Pt(18)
    tr.font.bold      = True
    tr.font.color.rgb = RGBColor(0xF0, 0xD0, 0x80)
    _set_rtl_run(tr)

    # Date
    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dp.paragraph_format.space_after = Pt(4)
    dr = dp.add_run(f"Recovered: {date_str}")
    dr.font.name      = LATIN_FONT
    dr.font.size      = Pt(9)
    dr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # Ornament
    op = doc.add_paragraph()
    op.alignment = WD_ALIGN_PARAGRAPH.CENTER
    op.paragraph_format.space_after = Pt(14)
    orr = op.add_run("✦   ✦   ✦")
    orr.font.name      = LATIN_FONT
    orr.font.size      = Pt(13)
    orr.font.color.rgb = RGBColor(0xB8, 0x86, 0x0B)

    # ── Content lines ─────────────────────────────────────────────────────
    for line in lines:
        verse = is_verse(line)

        if verse:
            # ── Persian/Arabic Masnavi verse — bold, centered, separated ──
            spacer = doc.add_paragraph()
            spacer.paragraph_format.line_spacing = Pt(6)
            spacer.paragraph_format.space_before = Pt(0)
            spacer.paragraph_format.space_after  = Pt(0)

            para = doc.add_paragraph()
            _set_rtl_para(para)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before  = Pt(8)
            para.paragraph_format.space_after   = Pt(8)
            para.paragraph_format.line_spacing  = Pt(36)
            para.paragraph_format.left_indent   = Inches(0.5)
            para.paragraph_format.right_indent  = Inches(0.5)
            _add_shading(para, "FDF0D0")
            _add_border_right(para, "B8860B", 24)

            run = para.add_run(line)
            run.font.name      = URDU_FONT
            run.font.size      = Pt(17)
            run.font.bold      = True
            run.font.color.rgb = RGBColor(0x4A, 0x2C, 0x00)
            _set_rtl_run(run)

            spacer2 = doc.add_paragraph()
            spacer2.paragraph_format.line_spacing = Pt(6)
            spacer2.paragraph_format.space_before = Pt(0)
            spacer2.paragraph_format.space_after  = Pt(0)

        else:
            # ── Urdu explanation text ──────────────────────────────────────
            para = doc.add_paragraph()
            _set_rtl_para(para)
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            para.paragraph_format.space_before  = Pt(2)
            para.paragraph_format.space_after   = Pt(2)
            para.paragraph_format.line_spacing  = Pt(30)

            run = para.add_run(line)
            run.font.name      = URDU_FONT
            run.font.size      = Pt(13)
            run.font.bold      = False
            run.font.color.rgb = RGBColor(0x1A, 0x14, 0x09)
            _set_rtl_run(run)

    # ── Footer ────────────────────────────────────────────────────────────
    fp = doc.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(18)
    fr = fp.add_run(
        f"Masnavi Lecture Transcription System  "
        f"|  Recovered from InPage file  |  {date_str}"
    )
    fr.font.name      = LATIN_FONT
    fr.font.size      = Pt(8)
    fr.font.color.rgb = RGBColor(0xA0, 0x80, 0x40)

    doc.save(out_path)
    return True


# ════════════════════════════════════════════════════════════════════════════════
# STEP 3 — Batch processor
# ════════════════════════════════════════════════════════════════════════════════

def process_file(inp_path: Path, out_dir: Path) -> dict:
    """Process one .inp file. Returns result dict."""
    out_path = out_dir / (inp_path.stem + ".docx")
    result   = {
        "file":    inp_path.name,
        "status":  "failed",
        "lines":   0,
        "output":  str(out_path),
        "error":   None,
    }

    try:
        # Extract text
        text = extract_text_from_inp(str(inp_path))
        lines = [l for l in text.splitlines() if l.strip()]

        if not lines:
            result["error"] = "No Urdu text found in file"
            return result

        result["lines"] = len(lines)

        # Build title from filename
        title = inp_path.stem.replace("_", " ").replace("-", " ")

        # Build DOCX
        ok = build_docx(title, lines, str(out_path))
        if ok:
            result["status"] = "success"
        else:
            result["error"] = "DOCX build failed"

    except Exception as e:
        import traceback
        result["error"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()

    return result


def check_dependencies():
    """Check all required packages are installed. Exit with clear message if not."""
    missing = []
    try:
        import docx
    except ImportError:
        missing.append("python-docx")

    if missing:
        print()
        print("=" * 60)
        print("  ERROR: Missing required package(s):")
        for pkg in missing:
            print(f"    - {pkg}")
        print()
        print("  Fix: run this command first:")
        print(f"    pip install {' '.join(missing)}")
        print()
        print("  If you are using a virtual environment (.venv):")
        print("    Make sure it is activated first:")
        print("    .venv\\Scripts\\activate   (Windows)")
        print("    Then run: pip install python-docx")
        print("=" * 60)
        print()
        sys.exit(1)


def batch_convert(inp_folder: str, out_folder: str):
    """Convert all .inp files in a folder to DOCX."""
    inp_dir = Path(inp_folder)
    out_dir = Path(out_folder)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find all .inp files
    inp_files = sorted(inp_dir.glob("*.inp"))

    if not inp_files:
        print(f"No .inp files found in: {inp_dir}")
        print("Make sure the folder path is correct and files have .inp extension.")
        return

    print()
    print("=" * 60)
    print(f"  InPage → DOCX Batch Converter")
    print(f"  Input  : {inp_dir}")
    print(f"  Output : {out_dir}")
    print(f"  Files  : {len(inp_files)} .inp files found")
    print("=" * 60)
    print()

    success = 0
    failed  = 0
    skipped = 0

    for i, inp_file in enumerate(inp_files, 1):
        out_path = out_dir / (inp_file.stem + ".docx")

        # Skip if already converted
        if out_path.exists():
            print(f"  [{i:3}/{len(inp_files)}] SKIP (already exists): {inp_file.name}")
            skipped += 1
            continue

        print(f"  [{i:3}/{len(inp_files)}] Converting: {inp_file.name} ...", end=" ", flush=True)
        result = process_file(inp_file, out_dir)

        if result["status"] == "success":
            size_kb = out_path.stat().st_size // 1024
            print(f"✓ {result['lines']} lines → {inp_file.stem}.docx ({size_kb} KB)")
            success += 1
        else:
            print(f"✗ FAILED — {result['error']}")
            if result.get("traceback"):
                # Show first line of traceback for debugging
                tb_line = [l.strip() for l in result["traceback"].splitlines() if l.strip()]
                if tb_line:
                    print(f"         {tb_line[-1]}")
            failed += 1

    # Summary
    print()
    print("=" * 60)
    print(f"  DONE")
    print(f"  ✓ Converted : {success}")
    print(f"  ✗ Failed    : {failed}")
    print(f"  ⏭ Skipped   : {skipped} (already existed)")
    print(f"  Output folder: {out_dir}")
    print("=" * 60)
    print()

    if failed > 0:
        print(f"  Note: {failed} file(s) failed. These may be too")
        print("  severely corrupted to recover any text from.")
    if success > 0:
        print(f"  Open DOCX files in Microsoft Word.")
        print("  Then copy-paste text into InPage to save as .inp")


# ════════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Convert corrupted InPage .inp files to Word DOCX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--folder", help="Folder containing .inp files (converts all)")
    group.add_argument("--file",   help="Single .inp file to convert")

    parser.add_argument(
        "--output", default=None,
        help="Output folder for DOCX files (default: 'recovered_docx' next to input)"
    )

    args = parser.parse_args()

    # Check dependencies first — gives clear error if python-docx missing
    check_dependencies()

    args = parser.parse_args()

    # Single file mode
    if args.file:
        inp_path = Path(args.file)
        if not inp_path.exists():
            print(f"File not found: {inp_path}")
            sys.exit(1)
        out_dir = Path(args.output) if args.output else inp_path.parent / "recovered_docx"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Converting: {inp_path.name}")
        result = process_file(inp_path, out_dir)
        if result["status"] == "success":
            print(f"✓ Done → {result['output']}  ({result['lines']} lines)")
        else:
            print(f"✗ Failed: {result['error']}")
        return

    # Batch folder mode
    inp_dir = Path(args.folder)
    if not inp_dir.exists():
        print(f"Folder not found: {inp_dir}")
        sys.exit(1)

    out_dir = Path(args.output) if args.output else inp_dir.parent / "recovered_docx"
    batch_convert(str(inp_dir), str(out_dir))


if __name__ == "__main__":
    main()
