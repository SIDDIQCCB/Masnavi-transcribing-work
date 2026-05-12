#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-time setup for Masnavi Transcription System
# Run once: bash setup.sh
# =============================================================================

set -e

echo ""
echo "======================================================"
echo "  مثنوی Transcription System — Setup"
echo "======================================================"
echo ""

# 1. Python check
python3 --version >/dev/null 2>&1 || { echo "ERROR: Python 3 is required."; exit 1; }
echo "[1/4] Python OK: $(python3 --version)"

# 2. pip install
echo "[2/4] Installing Python packages..."
pip3 install -r requirements.txt --quiet
echo "      Packages installed."

# 3. ffmpeg check
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[3/4] ffmpeg OK: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "[3/4] WARNING: ffmpeg not found."
    echo "      Please install ffmpeg:"
    echo "        Ubuntu/Debian : sudo apt install ffmpeg"
    echo "        macOS         : brew install ffmpeg"
    echo "        Windows       : https://ffmpeg.org/download.html"
fi

# 4. Create folders
mkdir -p transcripts audio_cache fonts
echo "[4/4] Folders created: transcripts/, audio_cache/"
echo "[5/5] Downloading Noto Nastaliq Urdu font for offline use..."
python3 download_font.py

echo ""
echo "======================================================"
echo "  Setup complete! How to use:"
echo ""
echo "  CLI (single video):"
echo "    python3 run_transcription.py --url 'https://youtube.com/watch?v=...'"
echo ""
echo "  CLI (full playlist):"
echo "    python3 run_transcription.py --playlist 'https://youtube.com/playlist?list=...'"
echo ""
echo "  Web UI:"
echo "    streamlit run app.py"
echo ""
echo "======================================================"
