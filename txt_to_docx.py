"""
txt_to_docx.py — Convert any transcript TXT file to Word DOCX

Usage:
    python3 txt_to_docx.py "your_file.txt"
    python3 txt_to_docx.py "transcripts/درس_مثنوی.txt"

Output:
    Same folder, same name, .docx extension
    Opens directly in Microsoft Word
"""

import sys
import re
from pathlib import Path
from datetime import datetime


def txt_to_docx(txt_path: str) -> str:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    URDU_FONT  = "Jameel Noori Nastaleeq"
    LATIN_FONT = "Calibri"
    RTL_RE     = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

    def is_verse(line):
        if len(line) >= 130: return False
        rtl   = len(RTL_RE.findall(line))
        total = len(line.replace(" ", ""))
        return total > 0 and (rtl / total) > 0.85 and len(line) < 120

    def is_header_line(line):
        return line.startswith("=") or any(
            line.startswith(k) for k in ["عنوان", "تاریخ", "ماخذ"]
        )

    def set_rtl_para(para):
        pPr  = para._p.get_or_add_pPr()
        bidi = OxmlElement("w:bidi")
        bidi.set(qn("w:val"), "1")
        pPr.insert(0, bidi)

    def set_rtl_run(run):
        rPr = run._r.get_or_add_rPr()
        rtl = OxmlElement("w:rtl")
        rtl.set(qn("w:val"), "1")
        rPr.append(rtl)

    def add_shading(para, fill_hex):
        pPr = para._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  fill_hex)
        pPr.append(shd)

    def add_border_right(para, color="B8860B", size=18):
        pPr  = para._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        right = OxmlElement("w:right")
        right.set(qn("w:val"),   "single")
        right.set(qn("w:sz"),    str(size))
        right.set(qn("w:space"), "6")
        right.set(qn("w:color"), color)
        pBdr.append(right)
        pPr.append(pBdr)

    # ── Read TXT ────────────────────────────────────────────────────────
    p       = Path(txt_path)
    content = p.read_text(encoding="utf-8")

    # Extract title and date from header if present
    title    = p.stem.replace("_", " ")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines    = []

    for line in content.splitlines():
        line = line.strip()
        if not line or is_header_line(line):
            # Extract title from header
            if line.startswith("عنوان"):
                title = line.split(":", 1)[-1].strip()
            elif line.startswith("تاریخ"):
                date_str = line.split(":", 1)[-1].strip()
            continue
        lines.append(line)

    # ── Build DOCX ──────────────────────────────────────────────────────
    doc     = Document()
    section = doc.sections[0]
    section.page_width   = Inches(8.27)
    section.page_height  = Inches(11.69)
    section.left_margin  = section.right_margin  = Inches(1.0)
    section.top_margin   = section.bottom_margin = Inches(1.0)

    # Title
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_rtl_para(tp)
    add_shading(tp, "1A1409")
    tp.paragraph_format.space_before = Pt(0)
    tp.paragraph_format.space_after  = Pt(6)
    tp.paragraph_format.line_spacing = Pt(36)
    tr = tp.add_run(title)
    tr.font.name      = URDU_FONT
    tr.font.size      = Pt(18)
    tr.font.bold      = True
    tr.font.color.rgb = RGBColor(0xF0, 0xD0, 0x80)
    set_rtl_run(tr)

    # Date
    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dp.paragraph_format.space_after = Pt(8)
    dr = dp.add_run(date_str)
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

    # Content
    for line in lines:
        verse = is_verse(line)
        para  = doc.add_paragraph()
        set_rtl_para(para)
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        para.paragraph_format.space_before = Pt(2)
        para.paragraph_format.space_after  = Pt(2)
        para.paragraph_format.line_spacing = Pt(28) if verse else Pt(32)

        if verse:
            add_shading(para, "FDF6E0")
            add_border_right(para)
            para.paragraph_format.left_indent  = Inches(0.3)
            para.paragraph_format.right_indent = Inches(0.2)

        run = para.add_run(line)
        run.font.name      = URDU_FONT
        run.font.size      = Pt(15) if verse else Pt(13)
        run.font.color.rgb = RGBColor(0x4A, 0x2C, 0x00) if verse else RGBColor(0x1A, 0x14, 0x09)
        set_rtl_run(run)

    # Footer
    fp = doc.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(18)
    fr = fp.add_run(f"Masnavi Lecture Transcription System  |  {date_str}")
    fr.font.name      = LATIN_FONT
    fr.font.size      = Pt(8)
    fr.font.color.rgb = RGBColor(0xA0, 0x80, 0x40)

    # Save
    out_path = p.with_suffix(".docx")
    doc.save(str(out_path))
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 txt_to_docx.py 'your_file.txt'")
        print("   or: python3 txt_to_docx.py transcripts/")
        print("       (converts ALL txt files in a folder)")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_dir():
        # Convert all TXT files in folder
        files = list(target.glob("*.txt"))
        print(f"Found {len(files)} TXT files in {target}")
        for i, f in enumerate(files, 1):
            try:
                out = txt_to_docx(str(f))
                print(f"  [{i}/{len(files)}] ✓ {f.name} → {Path(out).name}")
            except Exception as e:
                print(f"  [{i}/{len(files)}] ✗ {f.name} — Error: {e}")
        print("Done.")

    elif target.is_file() and target.suffix == ".txt":
        out = txt_to_docx(str(target))
        print(f"✓ Converted: {out}")

    else:
        print(f"Error: '{target}' is not a .txt file or folder.")
        sys.exit(1)
