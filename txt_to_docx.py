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

    
# Persian words common in Masnavi verses
_PERSIAN_WORDS = {
    "این","آن","است","می","را","که","از","با","بر","تا","هر","هم",
    "نی","بشنو","چون","شکایت","جدایی","حکایت","آتش","کاندر","فتاد",
    "دل","جان","درد","آب","خاک","باد","روح","نور",
    "گفت","گفتم","گویم","شنو","بین","بیا","رفت","آمد",
    "ما","من","تو","شد","شو","کن","کرد","بود","باش",
    "دوست","راه","راز","پرده","پنهان","آشکار",
    "مست","هست","نیست","چیست","کیست","کجاست",
    "جوشش","خاموش","آواز","ناله","فریاد",
    "می‌کند","می‌گوید","می‌خواهد","می‌داند",
}
_URDU_WORDS = {
    "ہے","ہیں","ہو","ہوں","ہوتا","ہوتی","ہوتے",
    "نے","کو","میں","سے","پر","کے","کی","کا",
    "یہ","وہ","اس","ان","جو","جب","تب","اور","لیکن",
    "فرمایا","کہا","بتایا","سمجھایا","بیان","مطلب",
    "آج","کل","پہلے","بعد","ابھی","پھر",
    "بہت","کچھ","سب","ہمارے","تمہارے","آپ",
    "مولانا","حضرت","شیخ","درس","سبق",
}
_STRONG_URDU    = {"ہے","ہیں","ہوتا","ہوتی","فرمایا","کہا","بتایا","مولانا","حضرت"}
_STRONG_PERSIAN = {"بشنو","کاندر","می‌کند","می‌گوید","جدایی","شکایت","فتاد","گفت"}


def is_verse(line: str) -> bool:
    """
    Detect Persian Masnavi verse vs Urdu explanation.
    Both use Arabic script so detection is vocabulary-based.
    """
    if not line.strip(): return False
    words = line.split()
    if len(words) > 20: return False
    clean = [w.strip("،۔؟!.") for w in words]
    if any(w in _STRONG_URDU    for w in clean): return False
    if any(w in _STRONG_PERSIAN for w in clean): return True
    persian = sum(1 for w in clean if w in _PERSIAN_WORDS)
    urdu    = sum(1 for w in clean if w in _URDU_WORDS)
    if persian > urdu and persian >= 2: return True
    if 2 <= len(words) <= 10 and urdu == 0 and persian >= 1: return True
    return False

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
