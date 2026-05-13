"""
Masnavi Transcription System — Team Dashboard
Run: streamlit run app.py
"""
import streamlit as st
import json, os, time, threading
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Masnavi Transcription",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

:root {
  --bg:       #0f1117;
  --surface:  #1a1d27;
  --surface2: #222635;
  --border:   #2e3347;
  --gold:     #f0b429;
  --gold2:    #ffd166;
  --green:    #06d6a0;
  --red:      #ef476f;
  --blue:     #118ab2;
  --text:     #e8eaf0;
  --muted:    #8b92a9;
  --urdu:     'Noto Nastaliq Urdu', serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  background: var(--bg) !important;
  color: var(--text) !important;
}

/* ── Fix sidebar toggle — always visible ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

[data-testid="collapsedControl"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  background: var(--gold) !important;
  color: #000 !important;
  border-radius: 0 8px 8px 0 !important;
  width: 28px !important;
  height: 48px !important;
  top: 50% !important;
  z-index: 9999 !important;
}
[data-testid="collapsedControl"] svg { fill: #000 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
}
[data-testid="stSidebar"] .stSlider > div > div {
  background: var(--border) !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
}

/* ── Main area ── */
.main { background: var(--bg) !important; }
.block-container {
  padding: 1.5rem 2rem 4rem !important;
  max-width: 1400px !important;
  background: var(--bg) !important;
}

/* ── Typography ── */
h1 { font-size: 1.8rem !important; font-weight: 700 !important;
     color: var(--text) !important; letter-spacing: -.02em !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important;
     color: var(--text) !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important;
     color: var(--muted) !important; text-transform: uppercase;
     letter-spacing: .08em !important; }
p, li { color: var(--text) !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 1.2rem 1.4rem !important;
}
[data-testid="metric-container"] label {
  color: var(--muted) !important;
  font-size: .7rem !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
  font-weight: 500 !important;
}
[data-testid="metric-container"] [data-testid="metric-value"] {
  color: var(--text) !important;
  font-size: 2rem !important;
  font-weight: 700 !important;
}

/* ── Buttons ── */
.stButton > button {
  background: var(--gold) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: .88rem !important;
  padding: .55rem 1.5rem !important;
  transition: all .2s !important;
  font-family: 'Inter', sans-serif !important;
}
.stButton > button:hover {
  background: var(--gold2) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:disabled {
  background: var(--border) !important;
  color: var(--muted) !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
  background: linear-gradient(90deg, var(--gold), var(--gold2)) !important;
  border-radius: 4px !important;
}
.stProgress > div {
  background: var(--border) !important;
  border-radius: 4px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border-radius: 10px !important;
  padding: 4px !important;
  gap: 2px !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--muted) !important;
  border-radius: 7px !important;
  font-weight: 500 !important;
  font-size: .85rem !important;
  padding: .45rem 1rem !important;
}
.stTabs [aria-selected="true"] {
  background: var(--gold) !important;
  color: #000 !important;
  font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] {
  padding: 0 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stSelectbox > div > div {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 2px rgba(240,180,41,.2) !important;
}

/* ── Radio ── */
.stRadio > div { gap: 8px !important; }
.stRadio label { color: var(--text) !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--surface2) !important;
  border: 1px dashed var(--border) !important;
  border-radius: 12px !important;
  padding: 1.5rem !important;
}
[data-testid="stFileUploader"] * { color: var(--text) !important; }

/* ── Custom components ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.2rem 1.4rem;
  margin: .5rem 0;
}
.card:hover { border-color: var(--gold); }

.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 20px;
  font-size: .72rem; font-weight: 600; letter-spacing: .04em;
}
.b-done  { background: rgba(6,214,160,.15);  color: #06d6a0; }
.b-pend  { background: rgba(255,209,102,.15); color: #ffd166; }
.b-proc  { background: rgba(17,138,178,.15);  color: #118ab2; }
.b-fail  { background: rgba(239,71,111,.15);  color: #ef476f; }
.b-corr  { background: rgba(240,180,41,.15);  color: #f0b429; }

.row {
  display: flex; align-items: center; gap: 12px;
  padding: .65rem 1rem;
  border-bottom: 1px solid var(--border);
  transition: background .15s;
}
.row:hover { background: var(--surface2); }
.row:last-child { border-bottom: none; }
.row-num { color: var(--muted); min-width: 30px; font-size: .75rem; }
.row-title { flex: 1; color: var(--text); font-size: .88rem; }
.row-urdu { flex: 1; font-family: var(--urdu); direction: rtl;
            text-align: right; font-size: .95rem; color: var(--text); }
.row-meta { font-size: .72rem; color: var(--muted); }

.section-header {
  font-size: .7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .12em; color: var(--muted);
  padding: .75rem 0 .4rem; margin-top: .5rem;
}
.divider { border: none; border-top: 1px solid var(--border); margin: 1rem 0; }

.stat-pill {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 20px; padding: 4px 12px; font-size: .8rem; color: var(--muted);
}
.stat-pill b { color: var(--text); }

.log-box {
  background: #0a0c12; color: #06d6a0;
  font-family: 'Courier New', monospace; font-size: .73rem;
  line-height: 1.7; padding: 1rem; border-radius: 10px;
  border: 1px solid var(--border);
  max-height: 200px; overflow-y: auto; white-space: pre-wrap;
}

.info-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--gold);
  border-radius: 0 10px 10px 0;
  padding: .9rem 1.2rem;
  margin: .5rem 0;
  font-size: .88rem;
  line-height: 1.7;
}

.page-title {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 1.5rem;
}
.page-title .icon {
  font-size: 2rem;
  background: linear-gradient(135deg, var(--gold), var(--gold2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

[data-testid="stSpinner"] { color: var(--gold) !important; }
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Caption / small text */
.stCaption { color: var(--muted) !important; }
small { color: var(--muted) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "videos": [], "logs": [], "processing": False,
    "cur_video": "", "cur_stage": "", "cur_pct": 0.0,
    "playlist_url": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

PROGRESS_FILE  = os.environ.get("PROGRESS_FILE",  "progress.json")
TRANSCRIPT_DIR = os.environ.get("TRANSCRIPT_DIR", "transcripts")
AUDIO_DIR      = os.environ.get("AUDIO_DIR",      "audio_cache")

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[-300:]

def load_tracker(pfile=PROGRESS_FILE):
    p = Path(pfile)
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except: pass
    return {}

def badge(status):
    m = {
        "completed": ("b-done",  "✓ مکمل"),
        "pending":   ("b-pend",  "⏳ باقی"),
        "processing":("b-proc",  "⚙ جاری"),
        "failed":    ("b-fail",  "✗ ناکام"),
        "corrected": ("b-corr",  "✎ درست"),
    }
    cls, lbl = m.get(status, ("b-pend", status))
    return f'<span class="badge {cls}">{lbl}</span>'

def get_file_stats(folder):
    p = Path(folder)
    if not p.exists(): return 0, 0, 0
    docx = list(p.glob("*.docx"))
    txt  = list(p.glob("*.txt"))
    size = sum(f.stat().st_size for f in docx + txt) / 1_048_576
    return len(docx), len(txt), round(size, 1)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:.5rem 0 1rem'>
      <div style='font-size:1.4rem;font-weight:700;color:#f0b429'>📜 مثنوی</div>
      <div style='font-size:.75rem;color:#8b92a9;margin-top:2px'>Transcription System</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">⚙ Transcription</div>', unsafe_allow_html=True)

    model_size  = st.selectbox("Model", ["tiny","base","small","medium","large-v2"], index=2,
                    help="small = fastest for your CPU. medium = better accuracy.")
    cpu_threads = st.slider("CPU Threads", 1, 8, 4,
                    help="Your i5-4570 has 4 cores — set to 4 for max speed")
    language    = st.selectbox("Language", ["auto (Urdu+Persian+English)","ur","fa"], index=0)
    lang_code   = None if "auto" in language else language

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📁 Folders</div>', unsafe_allow_html=True)

    out_dir   = st.text_input("Transcripts", TRANSCRIPT_DIR, label_visibility="collapsed",
                               placeholder="Transcripts folder")
    audio_dir = st.text_input("Audio cache", AUDIO_DIR, label_visibility="collapsed",
                               placeholder="Audio cache folder")
    prog_file = st.text_input("Progress file", PROGRESS_FILE, label_visibility="collapsed",
                               placeholder="progress.json")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📐 Model Guide</div>', unsafe_allow_html=True)
    for m, info in {
        "tiny":    "⚡⚡⚡⚡  Very fast, low accuracy",
        "small":   "⚡⚡⚡   Fast, good accuracy ✓",
        "medium":  "⚡⚡    Slower, better accuracy",
        "large-v2":"⚡      Slowest, best accuracy",
    }.items():
        st.markdown(f"<div style='font-size:.78rem;margin:.2rem 0'><code style='background:#2e3347;color:#f0b429;padding:1px 5px;border-radius:4px'>{m}</code> <span style='color:#8b92a9'>{info}</span></div>", unsafe_allow_html=True)


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-title">
  <span class="icon">📜</span>
  <div>
    <div style="font-size:1.6rem;font-weight:700;color:#e8eaf0">Masnavi Transcription System</div>
    <div style="font-size:.85rem;color:#8b92a9;margin-top:2px">مثنوی مولانا روم — Team Collaboration Dashboard</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_dash, tab_new, tab_files, tab_learn, tab_help = st.tabs([
    "📊  Dashboard", "🎬  Transcribe", "📂  Files", "🧠  Learn", "❓  Help"
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("")
    data       = load_tracker(prog_file)
    docx_count, txt_count, size_mb = get_file_stats(out_dir)

    # ── Top stats ─────────────────────────────────────────────────────────
    vids  = data.get("videos", {}) if data else {}
    total = data.get("total", 0)   if data else 0
    done  = sum(1 for v in vids.values() if v["status"] == "completed")
    proc  = sum(1 for v in vids.values() if v["status"] == "processing")
    fail  = sum(1 for v in vids.values() if v["status"] == "failed")
    pend  = sum(1 for v in vids.values() if v["status"] == "pending")
    pct   = round(done / max(total, 1) * 100, 1)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Videos",    total or "—")
    c2.metric("✅ Transcribed",  done)
    c3.metric("✎ Corrected",    docx_count,
              help="DOCX files in your transcripts folder")
    c4.metric("⏳ Pending",      pend)
    c5.metric("📄 TXT Files",    txt_count)
    c6.metric("💾 Storage",      f"{size_mb} MB")

    # ── Progress bar ──────────────────────────────────────────────────────
    if total > 0:
        st.markdown("")
        st.progress(pct / 100)
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;margin-top:4px">'
            f'<span style="font-size:.78rem;color:#8b92a9">{pct}% transcribed</span>'
            f'<span style="font-size:.78rem;color:#8b92a9">{done}/{total} videos</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("")

    # ── Corrected files section ────────────────────────────────────────────
    st.markdown('<div class="section-header">✎ Corrected Files</div>', unsafe_allow_html=True)

    docx_files = sorted(Path(out_dir).glob("*.docx"),
                        key=lambda f: f.stat().st_mtime, reverse=True) \
                 if Path(out_dir).exists() else []

    if docx_files:
        st.markdown(
            f'<div class="info-card">📂 <b>{len(docx_files)} corrected files</b> found in '
            f'<code>{out_dir}</code> folder. These are ready to paste into InPage.</div>',
            unsafe_allow_html=True
        )
        with st.expander(f"View all {len(docx_files)} corrected files"):
            for i, f in enumerate(docx_files, 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                kb    = f.stat().st_size // 1024
                st.markdown(
                    f'<div class="row">'
                    f'<span class="row-num">#{i}</span>'
                    f'<span class="row-title">{f.stem[:60]}</span>'
                    f'<span class="badge b-corr">✎ Corrected</span>'
                    f'<span class="row-meta">{mtime} · {kb}KB</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown('<div class="info-card">No corrected files yet. Transcribe a video, correct the DOCX, and upload it via the <b>Learn</b> tab.</div>', unsafe_allow_html=True)

    # ── Transcription progress ─────────────────────────────────────────────
    if vids:
        st.markdown("")
        st.markdown('<div class="section-header">🎬 Transcription Status</div>', unsafe_allow_html=True)

        fc1, fc2 = st.columns([2, 3])
        with fc1: flt    = st.selectbox("Filter", ["all","completed","pending","failed","processing"], key="df")
        with fc2: search = st.text_input("Search", placeholder="Search video title…", key="ds")

        shown = 0
        for i, (vid_id, info) in enumerate(vids.items(), 1):
            if flt != "all" and info["status"] != flt: continue
            title = info.get("title", vid_id)
            if search and search.lower() not in title.lower(): continue
            shown += 1
            b   = badge(info["status"])
            ts  = datetime.fromtimestamp(info["completed_at"]).strftime("%m/%d %H:%M") \
                  if info.get("completed_at") else ""
            doc = f'<span style="font-size:.72rem;color:#06d6a0">📄 DOCX</span>' \
                  if info.get("transcript_path") else ""
            st.markdown(
                f'<div class="row">'
                f'<span class="row-num">#{i}</span>'
                f'<span class="row-title">{title[:65]}</span>'
                f'{b}&nbsp;{doc}'
                f'<span class="row-meta">{ts}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        if shown == 0:
            st.caption("No videos match the filter.")
    elif not docx_files:
        st.markdown('<div class="info-card" style="margin-top:1rem">No transcription jobs yet. Go to the <b>Transcribe</b> tab to get started.</div>', unsafe_allow_html=True)

    # ── Live status ───────────────────────────────────────────────────────
    if st.session_state.processing:
        st.markdown("")
        st.markdown(
            f'<div class="card">'
            f'<div style="font-size:.8rem;color:#8b92a9;margin-bottom:6px">⚙ Processing</div>'
            f'<div style="font-weight:600">{st.session_state.cur_video[:70]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.progress(st.session_state.cur_pct / 100,
                    text=f"{st.session_state.cur_stage} — {st.session_state.cur_pct:.1f}%")
        time.sleep(3); st.rerun()

    if st.session_state.logs:
        st.markdown("")
        st.markdown('<div class="section-header">📋 Activity Log</div>', unsafe_allow_html=True)
        log_html = "\n".join(st.session_state.logs[-40:]).replace("<","&lt;")
        st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

    col_r, _ = st.columns([1, 6])
    with col_r:
        if st.button("↺ Refresh", key="dr"): st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRANSCRIBE
# ════════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.markdown("")
    st.markdown('<div class="section-header">🎬 New Transcription Job</div>', unsafe_allow_html=True)

    job_type  = st.radio("Type", ["Full Playlist", "Single Video"], horizontal=True)
    url_input = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/playlist?list=...  or  https://youtu.be/...",
        label_visibility="collapsed"
    )

    ca, cb, _ = st.columns([2, 2, 4])
    with ca:
        if st.button("🔍 Fetch Videos", use_container_width=True):
            if not url_input.strip():
                st.error("Please enter a URL first.")
            else:
                with st.spinner("Fetching…"):
                    try:
                        if job_type == "Full Playlist":
                            from transcriber import get_playlist_videos
                            vs = get_playlist_videos(url_input.strip())
                        else:
                            from transcriber import get_video_title
                            t  = get_video_title(url_input.strip()) or "Video"
                            vs = [{"id": "single", "url": url_input.strip(), "title": t}]
                        st.session_state.videos       = vs
                        st.session_state.playlist_url = url_input.strip()
                        add_log(f"Fetched {len(vs)} video(s)")
                    except Exception as e:
                        st.error(f"Error: {e}")

    if st.session_state.videos:
        st.markdown(
            f'<div class="info-card" style="margin:.75rem 0">✓ Found <b>{len(st.session_state.videos)}</b> video(s)</div>',
            unsafe_allow_html=True
        )
        for i, v in enumerate(st.session_state.videos[:15], 1):
            st.markdown(
                f'<div class="row"><span class="row-num">#{i}</span>'
                f'<span class="row-title">{v["title"][:70]}</span></div>',
                unsafe_allow_html=True
            )
        if len(st.session_state.videos) > 15:
            st.caption(f"… and {len(st.session_state.videos)-15} more")

    with cb:
        if st.button("▶ Start", use_container_width=True,
                     disabled=not st.session_state.videos or st.session_state.processing):

            def run_job(videos, model, lang, threads, odir, adir, pfile):
                try:
                    from progress_tracker import ProgressTracker
                    from transcriber import download_audio, transcribe_audio, save_transcript
                    tracker = ProgressTracker(save_path=pfile)
                    tracker.init_playlist(
                        st.session_state.playlist_url or videos[0]["url"], videos)
                    pending = tracker.pending_videos()
                    add_log(f"Started — {len(pending)} video(s) queued")

                    for vid_id, info in pending:
                        title = info["title"]; url = info["url"]
                        st.session_state.cur_video = title
                        st.session_state.cur_pct   = 0.0
                        tracker.mark_processing(vid_id)
                        add_log(f"▶ {title[:55]}")

                        def prog(stage, pct):
                            st.session_state.cur_stage = stage.replace("_"," ").title()
                            st.session_state.cur_pct   = pct

                        res = download_audio(url, adir, progress_cb=prog)
                        if not res or not res[0]:
                            tracker.mark_failed(vid_id, "Download failed")
                            add_log("  ✗ Download failed"); continue

                        audio_path, _ = res
                        add_log("  ✓ Downloaded")

                        transcript = transcribe_audio(
                            audio_path, language=lang, model_size=model,
                            progress_cb=prog, device="cpu",
                            compute_type="int8", cpu_threads=threads)

                        if os.path.exists(audio_path): os.remove(audio_path)
                        if not transcript:
                            tracker.mark_failed(vid_id,"Transcription failed")
                            add_log("  ✗ Failed"); continue

                        saved = save_transcript(title, transcript, odir)
                        tracker.mark_completed(vid_id, saved)
                        s = tracker.summary()
                        add_log(f"  ✓ Saved [{s['completed']}/{s['total']}]")

                    add_log("🎉 Batch complete!")
                except Exception as e:
                    add_log(f"Fatal: {e}")
                finally:
                    st.session_state.processing = False
                    st.session_state.cur_video  = ""

            st.session_state.processing = True
            threading.Thread(
                target=run_job,
                args=(st.session_state.videos, model_size, lang_code,
                      cpu_threads, out_dir, audio_dir, prog_file),
                daemon=True
            ).start()
            st.success("✓ Job started — watch progress in the Dashboard tab.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — FILES
# ════════════════════════════════════════════════════════════════════════════════
with tab_files:
    st.markdown("")
    st.markdown('<div class="section-header">📂 Transcript Files</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-card">Download DOCX → open in Word → correct errors → save → paste into InPage for printing.</div>',
        unsafe_allow_html=True
    )

    docx_list = sorted(Path(out_dir).glob("*.docx"),
                       key=lambda f: f.stat().st_mtime, reverse=True) \
                if Path(out_dir).exists() else []
    txt_list  = sorted(Path(out_dir).glob("*.txt"),
                       key=lambda f: f.stat().st_mtime, reverse=True) \
                if Path(out_dir).exists() else []

    if not docx_list and not txt_list:
        st.markdown(f'<div class="info-card">No files found in <code>{out_dir}</code> yet.</div>',
                    unsafe_allow_html=True)
    else:
        d1,d2,d3 = st.columns(3)
        d1.metric("📝 DOCX Files", len(docx_list))
        d2.metric("📄 TXT Files",  len(txt_list))
        total_mb = sum(f.stat().st_size for f in docx_list+txt_list) / 1_048_576
        d3.metric("💾 Total",      f"{total_mb:.1f} MB")

        st.markdown("")
        ft1, ft2 = st.tabs(["📝 DOCX — Edit & Print", "📄 TXT — Database"])

        with ft1:
            if not docx_list:
                st.caption("No DOCX files yet.")
            else:
                sd = st.text_input("Search files", placeholder="filter by name…", key="fds",
                                   label_visibility="collapsed")
                for f in docx_list:
                    if sd and sd.lower() not in f.stem.lower(): continue
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    kb    = f.stat().st_size // 1024
                    n, i, b2 = st.columns([4, 2, 1])
                    with n:
                        st.markdown(f'<div style="font-size:.88rem;color:#e8eaf0;padding:.3rem 0">📝 {f.stem[:55]}</div>',
                                    unsafe_allow_html=True)
                    with i:
                        st.markdown(f'<div style="font-size:.75rem;color:#8b92a9;padding:.4rem 0">{kb} KB · {mtime}</div>',
                                    unsafe_allow_html=True)
                    with b2:
                        st.download_button(
                            "⬇", data=f.read_bytes(), file_name=f.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{f.name}", use_container_width=True
                        )

        with ft2:
            if not txt_list:
                st.caption("No TXT files yet.")
            else:
                sel = st.selectbox("Select file to preview", [f.name for f in txt_list], key="tp")
                if sel:
                    fp = Path(out_dir) / sel
                    content = fp.read_text(encoding="utf-8")
                    rc, dc = st.columns([4, 1])
                    with rc: st.caption(f"{len(content):,} characters")
                    with dc:
                        st.download_button("⬇ Download", content.encode("utf-8"),
                                           file_name=sel, mime="text/plain; charset=utf-8",
                                           key="tdl")
                    st.code(content[:2500], language=None)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — LEARN
# ════════════════════════════════════════════════════════════════════════════════
with tab_learn:
    st.markdown("")
    st.markdown('<div class="section-header">🧠 Self-Improvement Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-card">Upload a corrected DOCX — the system automatically finds all differences '
        'from the original and learns from them. Every future transcription improves automatically.</div>',
        unsafe_allow_html=True
    )
    st.markdown("")

    try:
        from learner import get_stats
        stats = get_stats(prog_file.replace("progress.json","corrections.json"))
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("📚 Corrections Learned", stats.get("total_pairs", 0))
        s2.metric("📖 Episodes Fed Back",   stats.get("episodes_learned_from", 0))
        s3.metric("✅ Total Auto-Applied",  stats.get("total_corrections_applied", 0))
        s4.metric("🕐 Last Updated",
                  stats.get("last_updated","—")[:10] if stats.get("last_updated") else "—")

        if stats.get("top_corrections"):
            st.markdown("")
            st.markdown('<div class="section-header">🔝 Most Frequent Corrections</div>', unsafe_allow_html=True)
            for item in stats["top_corrections"][:8]:
                wrong   = item["wrong"]   or "(delete)"
                correct = item["correct"] or "(removed)"
                st.markdown(
                    f'<div class="row">'
                    f'<span style="flex:1;font-family:Noto Nastaliq Urdu,serif;direction:rtl;color:#ef476f">{wrong}</span>'
                    f'<span style="color:#8b92a9;padding:0 12px;font-size:.9rem">→</span>'
                    f'<span style="flex:1;font-family:Noto Nastaliq Urdu,serif;direction:rtl;color:#06d6a0">{correct}</span>'
                    f'<span style="color:#8b92a9;font-size:.75rem;min-width:50px">×{item["count"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    except:
        st.caption("No corrections learned yet.")

    st.markdown("")
    st.markdown('<div class="section-header">📤 Upload Corrected File</div>', unsafe_allow_html=True)

    col_up, col_info = st.columns([3, 2])
    with col_up:
        uploaded = st.file_uploader(
            "Drop your corrected DOCX here",
            type=["docx"],
            help="Correct the DOCX in Word, save it, then upload here."
        )
        txt_list_l = sorted(Path(out_dir).glob("*.txt"),
                            key=lambda f: f.stat().st_mtime, reverse=True) \
                     if Path(out_dir).exists() else []

        if uploaded:
            upload_stem = Path(uploaded.name).stem
            matched_txt = next((t for t in txt_list_l if t.stem == upload_stem), None)

            if matched_txt:
                st.success(f"✓ Matched: `{matched_txt.name}`")
            else:
                st.warning("Cannot auto-match — select the original TXT manually:")
                sel_txt     = st.selectbox("Original TXT", [f.name for f in txt_list_l])
                matched_txt = Path(out_dir) / sel_txt if sel_txt else None

            if matched_txt and st.button("🧠 Learn from this file", use_container_width=True):
                import tempfile, os as _os
                with st.spinner("Analysing differences…"):
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
                            tf.write(uploaded.read())
                            tmp = tf.name
                        from learner import learn_from_files
                        result = learn_from_files(
                            str(matched_txt), tmp,
                            corrections_path=prog_file.replace("progress.json","corrections.json")
                        )
                        _os.unlink(tmp)
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.success(
                                f"✅ Done!  {result['new_pairs']} new corrections,  "
                                f"{result['updated_pairs']} reinforced,  "
                                f"{result['total_in_db']} total in database."
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

    with col_info:
        st.markdown("""
<div class="info-card">
<b>Steps:</b><br>
1. Transcribe a video<br>
2. Download the DOCX from Files tab<br>
3. Correct all errors in Word<br>
4. Upload corrected file here<br>
5. System learns all differences<br>
6. Next transcription is better
</div>
<div class="info-card" style="margin-top:.5rem">
<b>What it learns:</b><br>
• Roman text → Urdu script<br>
• Wrong names → correct spelling<br>
• Misheard Islamic terms → correct<br>
• Any pattern you consistently fix
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — HELP
# ════════════════════════════════════════════════════════════════════════════════
with tab_help:
    st.markdown("")
    st.markdown('<div class="section-header">❓ How to Use</div>', unsafe_allow_html=True)

    steps = [
        ("1", "Transcribe a video", "Go to Transcribe tab → paste YouTube URL → Fetch → Start"),
        ("2", "Watch the Dashboard", "Dashboard shows every video status in real time"),
        ("3", "Download & Correct", "Files tab → download DOCX → fix in Word → save"),
        ("4", "Upload for Learning", "Learn tab → upload corrected DOCX → system improves"),
        ("5", "Paste into InPage", "Copy corrected text → paste into InPage → format for printing"),
        ("6", "Resume if stopped", "Just run the same command again — completed videos are skipped"),
    ]
    for num, title, desc in steps:
        st.markdown(
            f'<div class="card" style="display:flex;gap:1rem;align-items:flex-start">'
            f'<span style="background:#f0b429;color:#000;font-weight:700;'
            f'border-radius:50%;width:28px;height:28px;display:flex;align-items:center;'
            f'justify-content:center;font-size:.85rem;flex-shrink:0">{num}</span>'
            f'<div><div style="font-weight:600;margin-bottom:3px">{title}</div>'
            f'<div style="color:#8b92a9;font-size:.85rem">{desc}</div></div></div>',
            unsafe_allow_html=True
        )

    st.markdown("")
    st.markdown('<div class="section-header">🚀 Deploy Online</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="info-card">
<b>Streamlit Community Cloud (Free)</b><br>
1. Upload code to GitHub (private repo)<br>
2. Go to share.streamlit.io<br>
3. Select your repo → app.py → Deploy<br>
4. Share the URL with your team
</div>
<div class="info-card" style="margin-top:.5rem">
<b>Local Network (Free — same WiFi)</b><br>
<code>streamlit run app.py --server.address 0.0.0.0</code><br>
Anyone on same WiFi opens: http://YOUR_IP:8501
</div>
""", unsafe_allow_html=True)
