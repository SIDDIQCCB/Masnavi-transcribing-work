# 📜 مثنوی Lecture Transcription System

AI-powered tool to transcribe Urdu + Persian (Farsi) Masnavi lectures from YouTube into clean UTF-8 text files.

---

## Features

| Feature | Details |
|---|---|
| Mixed Urdu + Persian | Whisper `medium` model handles both languages |
| Long videos | 20–60 min lectures fully supported |
| Playlist automation | Processes 500+ videos one by one |
| Resume on crash | `progress.json` tracks every video; restart and it picks up where it left off |
| Arabic→Urdu normalization | Converts `الله` → `اللہ`, Arabic `ك/ي` → Urdu `ک/ی` etc. |
| CPU-only | No GPU required |
| Web UI | Streamlit dashboard with live progress |

---

## Quick Start

### 1. Install

```bash
# Clone / copy all files into a folder, then:
bash setup.sh
```

This installs `faster-whisper`, `yt-dlp`, and `streamlit`, and creates the `transcripts/` and `audio_cache/` folders.

**Prerequisite:** `ffmpeg` must be installed on your system.

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

---

### 2. Run (CLI)

**Single video:**
```bash
python3 run_transcription.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Full playlist:**
```bash
python3 run_transcription.py --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

**Resume interrupted job (same command — auto-detected):**
```bash
python3 run_transcription.py --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

---

### 3. Run (Web UI)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--url` | — | Single YouTube video URL |
| `--playlist` | — | YouTube playlist URL |
| `--model` | `medium` | Whisper model: `tiny / base / small / medium` |
| `--language` | `ur` | Primary language code |
| `--output` | `transcripts` | Output folder for text files |
| `--progress` | `progress.json` | Resume/progress tracking file |
| `--audio-dir` | `audio_cache` | Temp folder for downloaded audio |
| `--keep-audio` | off | Keep MP3 files after transcription |

---

## Model Guide

| Model | Size | Speed | Quality |
|---|---|---|---|
| tiny | 75 MB | Very fast | Low |
| base | 145 MB | Fast | OK for testing |
| small | 465 MB | Medium | Good |
| **medium** | **1.5 GB** | **Slower** | **✓ Recommended** |

For Urdu + Persian mixed audio, `medium` gives the best results on CPU.

---

## Output Files

```
transcripts/
    درس_مثنوی_حصہ_اول.txt
    Masnavi_Lecture_Part_2.txt
    ...
audio_cache/         ← auto-deleted after transcription
progress.json        ← resume tracking
```

Each `.txt` file starts with:
```
# Video Title
# Generated: 2024-xx-xx xx:xx:xx

[transcript text in Urdu/Persian]
```

---

## File Structure

```
masnavi_transcriber/
├── app.py               ← Streamlit web UI
├── run_transcription.py ← CLI batch runner
├── transcriber.py       ← Core engine (download + transcribe + normalize)
├── progress_tracker.py  ← Resume/progress JSON manager
├── requirements.txt
├── setup.sh
└── README.md
```

---

## Troubleshooting

**ffmpeg not found:**
```
ERROR: Postprocessing: ffprobe and ffmpeg not found.
```
→ Install ffmpeg (see Quick Start above)

**Model too slow:**
→ Use `--model small` instead of `medium`

**Wrong language detected:**
→ Already forced to `--language ur`. If Persian lines are being mangled, try `--language fa`.

**Resuming doesn't work:**
→ Make sure you point to the same `--progress progress.json` file as the original run.
