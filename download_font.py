"""
download_font.py — Run this ONCE to download Noto Nastaliq Urdu font locally.
After this, all HTML transcripts will work 100% offline on any device.

Usage:
    python3 download_font.py
"""

import urllib.request
import os
from pathlib import Path

FONTS_DIR = Path("fonts")

# Direct download URLs from Google Fonts CDN (static, versioned, reliable)
FONTS = [
    {
        "name": "NotoNastaliqUrdu-Regular",
        "url": "https://fonts.gstatic.com/s/notonastaliqurdu/v24/GGQBFJvgXcUG5VTF6bCjMgFwBNKKqpvBMgH5U7Wm3Iy0_L7oFy1fGV01-bBjM.woff2",
        "ext": "woff2",
    },
    {
        "name": "NotoNastaliqUrdu-Bold",
        "url": "https://fonts.gstatic.com/s/notonastaliqurdu/v24/GGQBFJvgXcUG5VTF6bCjMgFwBNKKqpvBMgH5U7Wm3Iy0_L7oFy1fGV0J-fBjM.woff2",
        "ext": "woff2",
    },
]

def download_fonts():
    FONTS_DIR.mkdir(exist_ok=True)
    print("\n📥 Downloading Noto Nastaliq Urdu fonts (one-time setup)...\n")

    all_ok = True
    for font in FONTS:
        dest = FONTS_DIR / f"{font['name']}.{font['ext']}"
        if dest.exists():
            print(f"  ✓ Already exists: {dest}")
            continue
        print(f"  Downloading {font['name']}...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(font["url"], dest)
            size_kb = dest.stat().st_size // 1024
            print(f"✓ ({size_kb} KB)")
        except Exception as e:
            print(f"✗ FAILED: {e}")
            all_ok = False

    print()
    if all_ok:
        print("✅ Fonts downloaded to fonts/ folder.")
        print("   All future HTML transcripts will be fully offline.\n")
    else:
        print("⚠️  Some fonts failed. Check your internet and try again.")
        print("   Transcripts will still work but will use the online font.\n")

if __name__ == "__main__":
    download_fonts()
