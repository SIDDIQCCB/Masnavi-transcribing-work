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
| Runs on any machine | Auto-detects NVIDIA GPU (CUDA) if present; otherwise runs on CPU. No manual config needed. |
| Web UI | ⚠️ Planned — `app.py` (Streamlit dashboard) is referenced below but not yet present in this project. CLI is the current supported interface. |

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| **Python** | **3.12.3** (required) | Newer versions (e.g. 3.13) have caused silent native crashes (`ctranslate2` + `MSVCP140.dll` access violations) on some CPUs. Stick to 3.12.x. |
| **Microsoft Visual C++ Redistributable (x64)** | Latest | Required by `ctranslate2`/`onnxruntime`. Download: https://aka.ms/vs/17/release/vc_redist.x64.exe — install even if it says "already installed" (choose Repair), then **reboot**. |
| **ffmpeg** | Any recent build | See below. |
| **NVIDIA GPU** | Optional | Only NVIDIA (CUDA) GPUs are used for acceleration. AMD/Intel integrated graphics are **not** supported by `ctranslate2` and are ignored — those machines always run on CPU. |

---

## Quick Start (Windows / PowerShell)

### 1. Install Python 3.12.3

Download from https://www.python.org/downloads/release/python-3123/ and install.
Confirm:
```powershell
py -3.12 --version
```

### 2. Create the virtual environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install the VC++ Redistributable

Download and run: https://aka.ms/vs/17/release/vc_redist.x64.exe
(Choose **Repair** if it says already installed, then restart your PC.)

### 4. Get ffmpeg

This project expects `ffmpeg.exe` and `ffprobe.exe` bundled inside the project folder:
```
Masnavi-Transcriber/
    ffmpeg/
        bin/
            ffmpeg.exe
            ffprobe.exe
```
Download a Windows build from https://www.gyan.dev/ffmpeg/builds/ (the "essentials" zip), extract it, and copy the `bin` folder contents into `ffmpeg\bin\` as shown above. Then add `ffmpeg\bin` to your PATH, or keep it project-local and the scripts will resolve it relatively.

Verify:
```powershell
ffmpeg -version
```

### 5. GPU acceleration (optional, NVIDIA only)

Nothing to configure — the script **auto-detects** an NVIDIA GPU via `ctranslate2` at startup and uses it automatically (`float16` on GPU vs `int8` on CPU). You'll see a line like:
```
Device auto-detect: cuda/float16 (NVIDIA GPU found)
```
or
```
Device auto-detect: cpu/int8 (no usable NVIDIA GPU — using CPU)
```
To force a specific device, pass `--device cpu` or `--device cuda` explicitly.

**`beam_size` also auto-adjusts** for accuracy: `5` on GPU (more thorough search, GPU is fast enough to afford it), `3` on CPU (keeps runtime reasonable on min-spec machines). Override with `--beam-size N` if needed.

**On a GPU machine (e.g. RTX 12GB), for maximum accuracy:**
```powershell
python run_transcription.py --url "..." --model large-v3
```
`large-v3` is impractically slow on CPU but runs comfortably on a 12GB GPU and gives a real accuracy improvement over `medium`, especially on mixed Urdu/Persian/English audio. `beam_size` and `chunk_length` widen automatically once GPU is detected — no extra flags needed beyond `--model`.

---

### 6. Run (CLI)

**Single video:**
```powershell
python run_transcription.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Full playlist:**
```powershell
python run_transcription.py --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

**Resume interrupted job (same command — auto-detected):**
```powershell
python run_transcription.py --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

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
| `--device` | `auto` | `auto` / `cpu` / `cuda` — auto-detects NVIDIA GPU |
| `--compute-type` | `auto` | `auto` picks `float16` (GPU) or `int8` (CPU) |
| `--beam-size` | `auto` | Auto: `5` on GPU, `3` on CPU. Higher = more accurate, slower |

---

## Model Guide

| Model | Size | Speed | Quality | Best for |
|---|---|---|---|---|
| tiny | 75 MB | Very fast | Low | Quick tests only |
| base | 145 MB | Fast | OK | Quick tests only |
| small | 465 MB | Medium | Good | CPU machines, faster turnaround |
| **medium** | **1.5 GB** | **Slower** | **✓ Good** | **CPU machines — recommended default** |
| large-v2 / large-v3 | ~3 GB | Slow on CPU, fast on GPU | Best | **NVIDIA GPU machines only** — impractically slow on CPU |

On CPU-only machines, `medium` is the best accuracy/speed tradeoff. On an NVIDIA GPU machine, use `--model large-v3` for the best accuracy — the GPU makes the extra size practical.

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
Masnavi-Transcriber/
├── .venv/                ← Python 3.12.3 virtual environment
├── ffmpeg/
│   └── bin/
│       ├── ffmpeg.exe
│       └── ffprobe.exe
├── run_transcription.py  ← CLI batch runner (entry point)
├── transcriber.py        ← Core engine (download + transcribe + normalize + save)
├── progress_tracker.py   ← Resume/progress JSON manager
├── batch_learn.py        ← Builds vocabulary from corrected episodes
├── learner.py             ← Applies learned corrections to new transcripts
├── download_font.py      ← Downloads Nastaliq font for DOCX output
├── requirements.txt
├── setup.sh               ← Linux/macOS setup only — not used on Windows, see Quick Start
├── progress.json          ← Created on first run
└── README.md
```

> **Note:** `app.py` (Streamlit web UI) is mentioned as a future feature but does not exist yet — see Features table above.

---

## Troubleshooting

**Program silently exits while "Loading model" — no error, no crash message:**
→ This is a native crash in `MSVCP140.dll`, usually caused by an outdated Visual C++ Redistributable.
1. Install/repair: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. **Reboot** (required — DLL changes need a restart)
3. Confirm with Windows **Event Viewer → Windows Logs → Application**, looking for an "Application Error" with `python.exe` as the faulting application — the faulting module name will confirm the DLL involved.

**Using Python 3.13 and things behave strangely:**
→ Use **Python 3.12.3** instead. This project was built and tested on 3.12.3; some native dependencies (`ctranslate2`) have had rough edges on very new Python versions.

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
