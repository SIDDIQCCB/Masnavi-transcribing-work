"""
Masnavi Transcription System
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

/* ═══════════════════════════════════════
   ROOT VARIABLES
═══════════════════════════════════════ */
:root {
  --bg:        #0d0f18;
  --card:      #161929;
  --card2:     #1e2235;
  --border:    #2a2f45;
  --gold:      #f5a623;
  --gold2:     #ffd166;
  --green:     #00c896;
  --red:       #ff4757;
  --blue:      #4da6ff;
  --purple:    #a855f7;
  --text:      #eceef5;
  --text2:     #9ba3be;
  --text3:     #636b87;
  --radius:    12px;
  --font:      'Inter', sans-serif;
  --font-ur:   'Noto Nastaliq Urdu', serif;
}

/* ═══════════════════════════════════════
   BASE
═══════════════════════════════════════ */
html, body, [class*="css"] {
  font-family: var(--font) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}
.main { background: var(--bg) !important; }
.block-container {
  padding: 1.8rem 2.5rem 5rem !important;
  max-width: 1500px !important;
}

/* ═══════════════════════════════════════
   HIDE STREAMLIT BRANDING ONLY
   (keep sidebar toggle visible!)
═══════════════════════════════════════ */
#MainMenu { visibility: hidden !important; }
footer    { visibility: hidden !important; }
/* Do NOT hide header — it contains the sidebar toggle */
header    { background: transparent !important; }
header [data-testid="stHeader"] { background: transparent !important; }

/* Make sidebar toggle button gold and always visible */
button[kind="header"] {
  background: var(--gold) !important;
  border-radius: 50% !important;
  color: #000 !important;
}
[data-testid="collapsedControl"] {
  background: var(--gold) !important;
  border-radius: 0 8px 8px 0 !important;
  color: #000 !important;
  visibility: visible !important;
  opacity: 1 !important;
}
[data-testid="collapsedControl"] svg { color: #000 !important; fill: #000 !important; }

/* ═══════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: var(--card) !important;
  border-right: 1px solid var(--border) !important;
  padding: 0 !important;
}
[data-testid="stSidebar"] > div { padding: 1rem !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--gold) !important;
  font-size: .9rem !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
  border: none !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
  margin: .75rem 0 !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input {
  background: var(--card2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
  font-size: .85rem !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: var(--text2) !important; font-size: .82rem !important; }
[data-testid="stSidebar"] .stSlider { padding: 0 !important; }

/* ═══════════════════════════════════════
   METRICS
═══════════════════════════════════════ */
[data-testid="metric-container"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 1.2rem 1.4rem !important;
  transition: border-color .2s !important;
}
[data-testid="metric-container"]:hover {
  border-color: var(--gold) !important;
}
[data-testid="metric-container"] label {
  color: var(--text3) !important;
  font-size: .7rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
}
[data-testid="metric-container"] [data-testid="metric-value"] {
  color: var(--text) !important;
  font-size: 2.2rem !important;
  font-weight: 700 !important;
  line-height: 1.1 !important;
}

/* ═══════════════════════════════════════
   BUTTONS
═══════════════════════════════════════ */
.stButton > button {
  background: linear-gradient(135deg, var(--gold), #e8920a) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  font-size: .85rem !important;
  padding: .6rem 1.6rem !important;
  letter-spacing: .02em !important;
  transition: all .2s !important;
  box-shadow: 0 2px 12px rgba(245,166,35,.25) !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px rgba(245,166,35,.4) !important;
}
.stButton > button:disabled {
  background: var(--border) !important;
  color: var(--text3) !important;
  box-shadow: none !important;
  transform: none !important;
}

/* ═══════════════════════════════════════
   TABS
═══════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background: var(--card) !important;
  border-radius: var(--radius) !important;
  padding: 5px !important;
  gap: 3px !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text2) !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: .83rem !important;
  padding: .5rem 1.2rem !important;
  transition: all .2s !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--text) !important;
  background: var(--card2) !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--gold), #e8920a) !important;
  color: #000 !important;
  font-weight: 700 !important;
  box-shadow: 0 2px 8px rgba(245,166,35,.3) !important;
}

/* ═══════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════ */
.stProgress > div {
  background: var(--border) !important;
  border-radius: 6px !important;
  height: 8px !important;
}
.stProgress > div > div {
  background: linear-gradient(90deg, var(--gold), var(--gold2)) !important;
  border-radius: 6px !important;
}

/* ═══════════════════════════════════════
   INPUTS
═══════════════════════════════════════ */
.stTextInput > div > div > input,
.stSelectbox > div > div {
  background: var(--card2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-size: .88rem !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(245,166,35,.15) !important;
}
.stTextInput label, .stSelectbox label { color: var(--text2) !important; font-size: .8rem !important; }

/* ═══════════════════════════════════════
   RADIO
═══════════════════════════════════════ */
.stRadio > label { color: var(--text2) !important; font-size: .82rem !important; }
.stRadio > div { gap: 6px !important; }
.stRadio > div > label { color: var(--text) !important; }

/* ═══════════════════════════════════════
   FILE UPLOADER
═══════════════════════════════════════ */
[data-testid="stFileUploader"] {
  background: var(--card2) !important;
  border: 2px dashed var(--border) !important;
  border-radius: var(--radius) !important;
  transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--gold) !important;
}
[data-testid="stFileUploader"] * { color: var(--text) !important; }

/* ═══════════════════════════════════════
   ALERTS
═══════════════════════════════════════ */
[data-testid="stAlert"] {
  background: var(--card2) !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
}

/* ═══════════════════════════════════════
   EXPANDER
═══════════════════════════════════════ */
.streamlit-expanderHeader {
  background: var(--card2) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}
.streamlit-expanderContent {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 0 8px 8px !important;
}

/* ═══════════════════════════════════════
   CUSTOM COMPONENTS
═══════════════════════════════════════ */
.page-header {
  display: flex; align-items: center; gap: 16px;
  padding: 1rem 0 1.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
}
.page-header .logo {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, var(--gold), #e8920a);
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.6rem;
  box-shadow: 0 4px 16px rgba(245,166,35,.3);
}
.page-header h1 {
  font-size: 1.5rem !important;
  font-weight: 800 !important;
  color: var(--text) !important;
  margin: 0 !important;
  line-height: 1.2 !important;
}
.page-header .subtitle {
  font-size: .82rem;
  color: var(--text3);
  margin-top: 3px;
  font-family: var(--font-ur);
  direction: rtl;
}

.section-title {
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .12em;
  color: var(--text3);
  margin: 1.4rem 0 .6rem;
}

.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.1rem 1.3rem;
  transition: all .2s;
}
.stat-card:hover { border-color: var(--gold); transform: translateY(-2px); }
.stat-card .label {
  font-size: .68rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .1em;
  color: var(--text3); margin-bottom: 6px;
}
.stat-card .value {
  font-size: 2rem; font-weight: 800; color: var(--text); line-height: 1;
}
.stat-card .sub {
  font-size: .75rem; color: var(--text3); margin-top: 4px;
}

.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 20px;
  font-size: .7rem; font-weight: 700; letter-spacing: .04em;
  white-space: nowrap;
}
.b-done  { background: rgba(0,200,150,.12);  color: #00c896; border: 1px solid rgba(0,200,150,.2); }
.b-pend  { background: rgba(245,166,35,.12); color: #f5a623; border: 1px solid rgba(245,166,35,.2); }
.b-proc  { background: rgba(77,166,255,.12); color: #4da6ff; border: 1px solid rgba(77,166,255,.2); }
.b-fail  { background: rgba(255,71,87,.12);  color: #ff4757; border: 1px solid rgba(255,71,87,.2); }
.b-corr  { background: rgba(168,85,247,.12); color: #a855f7; border: 1px solid rgba(168,85,247,.2); }

.row {
  display: flex; align-items: center; gap: 12px;
  padding: .7rem 1rem;
  border-bottom: 1px solid var(--border);
  transition: background .15s;
}
.row:hover { background: var(--card2); border-radius: 8px; }
.row:last-child { border-bottom: none; }
.row-num { color: var(--text3); min-width: 28px; font-size: .73rem; font-weight: 600; }
.row-title { flex: 1; color: var(--text); font-size: .86rem; }
.row-urdu {
  flex: 1; font-family: var(--font-ur);
  direction: rtl; text-align: right;
  font-size: .95rem; color: var(--text);
}
.row-meta { font-size: .72rem; color: var(--text3); white-space: nowrap; }

.info-card {
  background: var(--card2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--gold);
  border-radius: 0 var(--radius) var(--radius) 0;
  padding: 1rem 1.3rem;
  margin: .6rem 0;
  font-size: .86rem;
  line-height: 1.75;
  color: var(--text2);
}
.info-card b { color: var(--text); }
.info-card code {
  background: var(--border);
  color: var(--gold);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: .8rem;
}

.step-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  margin: .5rem 0;
  display: flex; gap: 14px; align-items: flex-start;
  transition: border-color .2s;
}
.step-card:hover { border-color: var(--gold); }
.step-num {
  width: 32px; height: 32px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--gold), #e8920a);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: .85rem; color: #000;
  box-shadow: 0 2px 8px rgba(245,166,35,.3);
}
.step-title { font-weight: 600; color: var(--text); font-size: .9rem; margin-bottom: 3px; }
.step-desc  { color: var(--text2); font-size: .82rem; line-height: 1.5; }

.log-box {
  background: #080a12;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: #00c896;
  font-family: 'Courier New', monospace;
  font-size: .73rem; line-height: 1.7;
  padding: 1rem 1.2rem;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.progress-live {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.2rem 1.4rem;
  margin: .8rem 0;
}
.progress-live .title {
  font-weight: 600; font-size: .9rem;
  color: var(--text); margin-bottom: .5rem;
}
.progress-live .stage {
  font-size: .75rem; color: var(--text3); margin-bottom: .4rem;
}

/* Correction arrow */
.correction-row {
  display: flex; align-items: center; gap: 8px;
  padding: .6rem 1rem;
  border-bottom: 1px solid var(--border);
}
.correction-row .wrong  { flex:1; color: #ff4757; font-family: var(--font-ur); direction:rtl; text-align:right; }
.correction-row .arrow  { color: var(--text3); font-size: 1rem; }
.correction-row .right  { flex:1; color: #00c896; font-family: var(--font-ur); direction:rtl; text-align:right; }
.correction-row .cnt    { color: var(--text3); font-size: .72rem; min-width: 40px; text-align:right; }

/* Scrollbar */
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--card); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }

/* Caption */
.stCaption, small { color: var(--text3) !important; font-size: .78rem !important; }
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

def badge_html(status):
    m = {
        "completed": ("b-done", "✓ مکمل"),
        "pending":   ("b-pend", "⏳ باقی"),
        "processing":("b-proc", "⚙ جاری"),
        "failed":    ("b-fail", "✗ ناکام"),
        "corrected": ("b-corr", "✎ Corrected"),
    }
    cls, lbl = m.get(status, ("b-pend", status))
    return f'<span class="badge {cls}">{lbl}</span>'

def get_folder_stats(folder):
    p = Path(folder)
    if not p.exists(): return 0, 0, 0
    docx = list(p.glob("*.docx"))
    txt  = list(p.glob("*.txt"))
    mb   = round(sum(f.stat().st_size for f in docx + txt) / 1_048_576, 1)
    return len(docx), len(txt), mb

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:.4rem 0 .8rem'>
      <div style='font-size:1.5rem;font-weight:800;
           background:linear-gradient(135deg,#f5a623,#ffd166);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
        📜 مثنوی
      </div>
      <div style='font-size:.73rem;color:#636b87;margin-top:2px'>
        Transcription System v2.0
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎙 Model")
    model_size = st.selectbox(
        "Whisper Model", ["tiny","base","small","medium","large-v2"],
        index=2, label_visibility="collapsed",
        help="small = best for your i5 CPU. medium = more accurate but slower."
    )
    st.caption({
        "tiny":    "⚡⚡⚡⚡  Very fast · Low accuracy",
        "base":    "⚡⚡⚡  Fast · Basic accuracy",
        "small":   "⚡⚡  Good speed · Good accuracy ✓",
        "medium":  "⚡  Slower · High accuracy",
        "large-v2":"🐢  Slowest · Best accuracy",
    }.get(model_size, ""))

    st.markdown("### 🖥 CPU")
    cpu_threads = st.slider("Threads", 1, 8, 4, label_visibility="collapsed",
                             help="Your i5-4570 has 4 cores — set to 4")
    st.caption(f"Using {cpu_threads} of your CPU cores")

    st.markdown("### 🌐 Language")
    language  = st.selectbox("Language", [
        "auto — Urdu + Persian + English",
        "ur — Urdu only",
        "fa — Persian only"
    ], index=0, label_visibility="collapsed")
    lang_code = None if "auto" in language else language[:2]

    st.markdown("---")
    st.markdown("### 📁 Folders")
    out_dir   = st.text_input("Transcripts", TRANSCRIPT_DIR, label_visibility="collapsed",
                               placeholder="transcripts folder")
    audio_dir = st.text_input("Audio Cache", AUDIO_DIR, label_visibility="collapsed",
                               placeholder="audio_cache folder")
    prog_file = st.text_input("Progress JSON", PROGRESS_FILE, label_visibility="collapsed",
                               placeholder="progress.json")

    st.markdown("---")
    docx_n, txt_n, mb = get_folder_stats(out_dir)
    st.markdown(f"""
    <div style='background:#1e2235;border-radius:10px;padding:.9rem 1rem'>
      <div style='font-size:.68rem;font-weight:700;text-transform:uppercase;
           letter-spacing:.1em;color:#636b87;margin-bottom:.6rem'>Storage</div>
      <div style='display:flex;justify-content:space-between;margin:.3rem 0'>
        <span style='font-size:.8rem;color:#9ba3be'>DOCX files</span>
        <span style='font-size:.8rem;font-weight:700;color:#a855f7'>{docx_n}</span>
      </div>
      <div style='display:flex;justify-content:space-between;margin:.3rem 0'>
        <span style='font-size:.8rem;color:#9ba3be'>TXT files</span>
        <span style='font-size:.8rem;font-weight:700;color:#4da6ff'>{txt_n}</span>
      </div>
      <div style='display:flex;justify-content:space-between;margin:.3rem 0'>
        <span style='font-size:.8rem;color:#9ba3be'>Total size</span>
        <span style='font-size:.8rem;font-weight:700;color:#f5a623'>{mb} MB</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
  <div class="logo">📜</div>
  <div>
    <h1>Masnavi Transcription System</h1>
    <div class="subtitle">مثنوی مولانا روم — ٹیم ڈیش بورڈ</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_dash, tab_new, tab_files, tab_learn, tab_help = st.tabs([
    "📊  Dashboard",
    "🎬  Transcribe",
    "📂  Files",
    "🧠  Learn",
    "❓  Help",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("")

    data       = load_tracker(prog_file)
    vids       = data.get("videos", {}) if data else {}
    total      = data.get("total", 0)   if data else 0
    done       = sum(1 for v in vids.values() if v["status"] == "completed")
    proc       = sum(1 for v in vids.values() if v["status"] == "processing")
    fail       = sum(1 for v in vids.values() if v["status"] == "failed")
    pend       = sum(1 for v in vids.values() if v["status"] == "pending")
    pct        = round(done / max(total, 1) * 100, 1)
    docx_n, txt_n, mb = get_folder_stats(out_dir)

    # ── Metrics row ───────────────────────────────────────────────────────
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("📹 Total Videos",  total or "—")
    c2.metric("✅ Transcribed",   done)
    c3.metric("✎ Corrected",     docx_n)
    c4.metric("⏳ Pending",       pend)
    c5.metric("❌ Failed",        fail)
    c6.metric("💾 Storage",       f"{mb} MB")

    # ── Progress bar ──────────────────────────────────────────────────────
    if total > 0:
        st.markdown("")
        st.progress(pct / 100)
        col_l, col_r = st.columns(2)
        col_l.caption(f"{pct}% of playlist transcribed")
        col_r.caption(f"{done} done · {pend} pending · {total} total")

    # ── Corrected files ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">✎ Corrected Files</div>', unsafe_allow_html=True)
    docx_files = sorted(
        Path(out_dir).glob("*.docx"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(out_dir).exists() else []

    if docx_files:
        st.markdown(
            f'<div class="info-card">Found <b>{len(docx_files)} corrected DOCX files</b> in '
            f'<code>{out_dir}/</code>. Ready to copy into InPage.</div>',
            unsafe_allow_html=True
        )
        with st.expander(f"📂 View all {len(docx_files)} corrected files"):
            for i, f in enumerate(docx_files, 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                kb    = f.stat().st_size // 1024
                st.markdown(
                    f'<div class="row">'
                    f'<span class="row-num">#{i}</span>'
                    f'<span class="row-title">{f.stem[:60]}</span>'
                    f'<span class="badge b-corr">✎ Corrected</span>'
                    f'<span class="row-meta">{mtime} · {kb} KB</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            '<div class="info-card">No corrected files yet in the transcripts folder.</div>',
            unsafe_allow_html=True
        )

    # ── Video status ──────────────────────────────────────────────────────
    if vids:
        st.markdown('<div class="section-title">🎬 Transcription Status</div>', unsafe_allow_html=True)
        fc1, fc2 = st.columns([2, 3])
        with fc1:
            flt = st.selectbox("Filter", ["all","completed","pending","failed","processing"], key="df")
        with fc2:
            srch = st.text_input("Search", placeholder="Search video title…", key="ds",
                                  label_visibility="collapsed")

        rows_html = ""
        shown = 0
        for i, (vid_id, info) in enumerate(vids.items(), 1):
            if flt != "all" and info["status"] != flt: continue
            title = info.get("title", vid_id)
            if srch and srch.lower() not in title.lower(): continue
            shown += 1
            b  = badge_html(info["status"])
            ts = datetime.fromtimestamp(info["completed_at"]).strftime("%m/%d %H:%M") \
                 if info.get("completed_at") else ""
            doc = '<span style="color:#00c896;font-size:.72rem">📄</span>' \
                  if info.get("transcript_path") else ""
            rows_html += (
                f'<div class="row">'
                f'<span class="row-num">#{i}</span>'
                f'<span class="row-title">{title[:65]}</span>'
                f'{b} {doc}'
                f'<span class="row-meta">{ts}</span>'
                f'</div>'
            )
        if rows_html:
            st.markdown(rows_html, unsafe_allow_html=True)
        elif shown == 0:
            st.caption("No videos match this filter.")

    elif not docx_files:
        st.markdown(
            '<div class="info-card" style="margin-top:1rem">No jobs yet. '
            'Go to the <b>Transcribe</b> tab to start.</div>',
            unsafe_allow_html=True
        )

    # ── Live processing status ────────────────────────────────────────────
    # Check if transcription process is still running
    pid_file = Path("transcription.pid")
    log_file = Path("transcription.log")
    is_running = False

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            import psutil
            is_running = psutil.Process(pid).is_running()
        except Exception:
            # psutil not available — check via os
            try:
                os.kill(pid, 0)
                is_running = True
            except Exception:
                is_running = False

    if is_running:
        st.markdown(
            '<div class="progress-live">'
            '<div class="stage">⚙ Transcription running in background…</div>'
            '<div class="title">Check progress.json for current video status</div>'
            '</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="info-card">✅ Process is running. '
            'Refresh this page every minute to see updates. '
            'Transcripts appear in the Files tab as they complete.</div>',
            unsafe_allow_html=True
        )

    # ── Show transcription log ────────────────────────────────────────────
    if log_file.exists():
        log_content = log_file.read_text(encoding="utf-8", errors="ignore")
        if log_content.strip():
            st.markdown('<div class="section-title">📋 Transcription Log</div>',
                        unsafe_allow_html=True)
            # Show last 40 lines
            lines    = log_content.strip().splitlines()
            last_40  = "\n".join(lines[-40:])
            safe_log = last_40.replace("<","&lt;").replace(">","&gt;")
            st.markdown(f'<div class="log-box">{safe_log}</div>',
                        unsafe_allow_html=True)
    elif st.session_state.logs:
        st.markdown('<div class="section-title">📋 Activity Log</div>',
                    unsafe_allow_html=True)
        log_html = "\n".join(st.session_state.logs[-40:]).replace("<","&lt;").replace(">","&gt;")
        st.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

    _, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button("↺ Refresh", key="dr"): st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRANSCRIBE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.markdown("")
    st.markdown('<div class="section-title">🎬 New Transcription Job</div>', unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        job_type  = st.radio("Job type", ["Full Playlist","Single Video"], horizontal=True)
        url_input = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/playlist?list=...  or  https://youtu.be/..."
        )

        ca, cb, _ = st.columns([2, 2, 3])
        with ca:
            fetch_btn = st.button("🔍 Fetch Videos", use_container_width=True)
        with cb:
            start_btn = st.button(
                "▶ Start",
                use_container_width=True,
                disabled=not st.session_state.videos or st.session_state.processing
            )

        if fetch_btn:
            if not url_input.strip():
                st.error("Enter a URL first.")
            else:
                with st.spinner("Fetching video list…"):
                    try:
                        if job_type == "Full Playlist":
                            from transcriber import get_playlist_videos
                            vs = get_playlist_videos(url_input.strip())
                        else:
                            from transcriber import get_video_title
                            t  = get_video_title(url_input.strip()) or "Video"
                            vs = [{"id":"single","url":url_input.strip(),"title":t}]
                        st.session_state.videos       = vs
                        st.session_state.playlist_url = url_input.strip()
                        add_log(f"Fetched {len(vs)} video(s)")
                    except Exception as e:
                        st.error(f"Error: {e}")

        if start_btn and st.session_state.videos:
            # ── Write a job config file ────────────────────────────────────
            # We launch run_transcription.py as a SEPARATE PROCESS.
            # This is the correct way — threading.Thread(daemon=True) gets
            # killed every time Streamlit reruns the page, which is why
            # transcription was stopping at 0%.
            # A subprocess runs completely independently of Streamlit.
            import subprocess, sys, json as _json

            job_cfg = {
                "url":       st.session_state.playlist_url,
                "job_type":  job_type,
                "model":     model_size,
                "language":  lang_code,
                "threads":   cpu_threads,
                "output":    out_dir,
                "audio_dir": audio_dir,
                "progress":  prog_file,
            }
            # Save job config
            cfg_path = Path("current_job.json")
            cfg_path.write_text(_json.dumps(job_cfg, ensure_ascii=False), encoding="utf-8")

            # Build command
            flag = "--playlist" if job_type == "Full Playlist" else "--url"
            cmd  = [
                sys.executable,
                "run_transcription.py",
                flag, st.session_state.playlist_url,
                "--model",    model_size,
                "--threads",  str(cpu_threads),
                "--output",   out_dir,
                "--audio-dir",audio_dir,
                "--progress", prog_file,
            ]
            if lang_code:
                cmd += ["--language", lang_code]

            try:
                # Open log file for subprocess output
                log_f = open("transcription.log", "w", encoding="utf-8")
                proc  = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=log_f,
                    cwd=str(Path(__file__).parent),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,
                )
                # Save PID so we can check if still running
                Path("transcription.pid").write_text(str(proc.pid))
                st.session_state.processing = True
                add_log(f"Transcription process started (PID {proc.pid})")
                add_log(f"Running: {' '.join(cmd[:4])}…")
                st.success(
                    f"✅ Transcription started in background (PID {proc.pid})\n\n"
                    "Switch to the **Dashboard** tab to watch progress. "
                    "The process runs independently — you can even close this tab."
                )
            except Exception as e:
                st.error(f"Failed to start process: {e}")
                add_log(f"Start failed: {e}")

    with right:
        if st.session_state.videos:
            st.markdown(
                f'<div class="info-card"><b>{len(st.session_state.videos)}</b> videos fetched</div>',
                unsafe_allow_html=True
            )
            for i, v in enumerate(st.session_state.videos[:12], 1):
                st.markdown(
                    f'<div class="row">'
                    f'<span class="row-num">#{i}</span>'
                    f'<span class="row-title">{v["title"][:55]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if len(st.session_state.videos) > 12:
                st.caption(f"… and {len(st.session_state.videos)-12} more")
        else:
            st.markdown("""
            <div class="info-card">
            <b>How to use:</b><br>
            1. Paste a YouTube URL above<br>
            2. Click <b>Fetch Videos</b><br>
            3. Click <b>Start</b> to begin<br>
            4. Watch progress in Dashboard
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FILES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_files:
    st.markdown("")
    st.markdown('<div class="section-title">📂 Transcript Files</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-card">Download DOCX → correct in Microsoft Word → '
        'copy text → paste into InPage for printing.</div>',
        unsafe_allow_html=True
    )

    docx_list = sorted(
        Path(out_dir).glob("*.docx"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(out_dir).exists() else []
    txt_list = sorted(
        Path(out_dir).glob("*.txt"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(out_dir).exists() else []

    if not docx_list and not txt_list:
        st.markdown(
            f'<div class="info-card">No files found in <code>{out_dir}</code> yet.</div>',
            unsafe_allow_html=True
        )
    else:
        d1,d2,d3 = st.columns(3)
        d1.metric("📝 DOCX",  len(docx_list))
        d2.metric("📄 TXT",   len(txt_list))
        d3.metric("💾 Size",  f"{round(sum(f.stat().st_size for f in docx_list+txt_list)/1_048_576,1)} MB")

        st.markdown("")
        ft1, ft2 = st.tabs(["📝 DOCX — Edit & Print", "📄 TXT — Database"])

        with ft1:
            if not docx_list:
                st.caption("No DOCX files yet.")
            else:
                sd = st.text_input("Search", placeholder="Filter by filename…",
                                    key="fds", label_visibility="collapsed")
                for f in docx_list:
                    if sd and sd.lower() not in f.stem.lower(): continue
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    kb    = f.stat().st_size // 1024
                    n, meta_col, btn_col = st.columns([4, 2, 1])
                    with n:
                        st.markdown(
                            f'<div style="padding:.35rem 0;color:#eceef5;font-size:.86rem">'
                            f'📝 {f.stem[:55]}</div>',
                            unsafe_allow_html=True
                        )
                    with meta_col:
                        st.markdown(
                            f'<div style="padding:.4rem 0;color:#636b87;font-size:.75rem">'
                            f'{kb} KB · {mtime}</div>',
                            unsafe_allow_html=True
                        )
                    with btn_col:
                        st.download_button(
                            "⬇", data=f.read_bytes(), file_name=f.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{f.name}", use_container_width=True
                        )

        with ft2:
            if not txt_list:
                st.caption("No TXT files yet.")
            else:
                sel = st.selectbox("Select file", [f.name for f in txt_list], key="tp")
                if sel:
                    fp      = Path(out_dir) / sel
                    content = fp.read_text(encoding="utf-8")
                    rc, dc  = st.columns([4, 1])
                    with rc: st.caption(f"{len(content):,} characters")
                    with dc:
                        st.download_button(
                            "⬇ Download", content.encode("utf-8"),
                            file_name=sel, mime="text/plain; charset=utf-8", key="tdl"
                        )
                    st.code(content[:2500], language=None)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — LEARN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_learn:
    st.markdown("")
    st.markdown('<div class="section-title">🧠 Self-Improvement Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-card">Upload a corrected DOCX. The system automatically finds '
        'every difference between the AI output and your correction, and learns from all '
        'of them at once. Every future transcription will be better.</div>',
        unsafe_allow_html=True
    )

    st.markdown("")
    try:
        from learner import get_stats
        stats   = get_stats(prog_file.replace("progress.json","corrections.json"))
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("📚 Corrections Learned", stats.get("total_pairs", 0))
        s2.metric("📖 Episodes Fed Back",   stats.get("episodes_learned_from", 0))
        s3.metric("✅ Auto-Applied Total",  stats.get("total_corrections_applied", 0))
        s4.metric("🕐 Last Updated",
                  stats.get("last_updated","—")[:10] if stats.get("last_updated") else "—")
        if stats.get("top_corrections"):
            st.markdown("")
            st.markdown('<div class="section-title">Top Corrections Learned</div>', unsafe_allow_html=True)
            for item in stats["top_corrections"][:8]:
                st.markdown(
                    f'<div class="correction-row">'
                    f'<span class="wrong">{item.get("wrong","") or "(delete)"}</span>'
                    f'<span class="arrow">→</span>'
                    f'<span class="right">{item.get("correct","") or "(removed)"}</span>'
                    f'<span class="cnt">×{item["count"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    except:
        st.caption("No corrections learned yet — upload your first corrected file below.")

    st.markdown("")
    left_l, right_l = st.columns([3, 2])
    with left_l:
        st.markdown('<div class="section-title">Upload Corrected DOCX</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop corrected DOCX here",
            type=["docx"],
            label_visibility="collapsed"
        )
        txt_list_l = sorted(
            Path(out_dir).glob("*.txt"),
            key=lambda f: f.stat().st_mtime, reverse=True
        ) if Path(out_dir).exists() else []

        if uploaded:
            upload_stem = Path(uploaded.name).stem
            matched_txt = next((t for t in txt_list_l if t.stem == upload_stem), None)
            if matched_txt:
                st.success(f"✓ Auto-matched: `{matched_txt.name}`")
            else:
                st.warning("Could not auto-match — select original TXT:")
                sel_txt     = st.selectbox("Original TXT", [f.name for f in txt_list_l])
                matched_txt = Path(out_dir) / sel_txt if sel_txt else None

            if matched_txt and st.button("🧠 Learn from this file", use_container_width=True):
                import tempfile, os as _os
                with st.spinner("Analysing all differences…"):
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
                                f"✅ Done!  "
                                f"{result['new_pairs']} new ·  "
                                f"{result['updated_pairs']} reinforced ·  "
                                f"{result['total_in_db']} total in database"
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

    with right_l:
        st.markdown("""
        <div class="info-card">
        <b>Workflow:</b><br>
        1. Transcribe a video<br>
        2. Download DOCX from Files tab<br>
        3. Open in Word, fix all errors<br>
        4. Upload corrected file here<br>
        5. System learns everything<br>
        6. Next video is more accurate
        </div>
        <div class="info-card" style="margin-top:.5rem">
        <b>What it learns:</b><br>
        • English text → Urdu script<br>
        • Wrong names → correct spelling<br>
        • Misheard Islamic terms<br>
        • Any pattern you correct
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — HELP
# ═══════════════════════════════════════════════════════════════════════════════
with tab_help:
    st.markdown("")
    st.markdown('<div class="section-title">How to Use</div>', unsafe_allow_html=True)
    for num, title, desc in [
        ("1","Transcribe a video",   "Transcribe tab → paste YouTube URL → Fetch → Start"),
        ("2","Watch the Dashboard",  "Dashboard shows every video — status, timestamps, files"),
        ("3","Download & Correct",   "Files tab → download DOCX → fix in Word → save"),
        ("4","Upload for Learning",  "Learn tab → upload corrected DOCX → system improves"),
        ("5","Paste into InPage",    "Copy corrected text → paste into InPage → format & print"),
        ("6","Resume if stopped",    "Run same command again — completed videos always skipped"),
    ]:
        st.markdown(
            f'<div class="step-card">'
            f'<div class="step-num">{num}</div>'
            f'<div><div class="step-title">{title}</div>'
            f'<div class="step-desc">{desc}</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("")
    st.markdown('<div class="section-title">Deploy Online</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-card">
    <b>Streamlit Community Cloud (Free)</b><br>
    1. Upload code to GitHub → go to share.streamlit.io → select app.py → Deploy<br>
    2. Share URL with your team — works on any phone or laptop
    </div>
    <div class="info-card" style="margin-top:.5rem">
    <b>Local Network (same WiFi — Free)</b><br>
    <code>streamlit run app.py --server.address 0.0.0.0</code><br>
    Team opens: http://YOUR_IP:8501
    </div>
    """, unsafe_allow_html=True)
