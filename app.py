"""
Masnavi AI — Team Dashboard (Standalone)
=========================================
This file works completely on its own.
No other Python files needed.
Deploy directly to Streamlit Cloud.

What this app does:
- Shows transcription progress to the whole team
- Lets team members download DOCX files
- Shows which videos are done / pending
- Reads progress.json and transcripts/ folder

What this app does NOT do:
- Does NOT run transcription (that runs on local PC via CLI)
- Does NOT need transcriber.py, learner.py etc on the server

Run locally : streamlit run app.py
Deploy      : push only this file + requirements.txt to GitHub
"""

import streamlit as st
import json, os, time
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Masnavi AI",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Config ────────────────────────────────────────────────────────────────────
PROGRESS_FILE  = os.environ.get("PROGRESS_FILE",  "progress.json")
TRANSCRIPT_DIR = os.environ.get("TRANSCRIPT_DIR", "transcripts")
GITHUB_URL     = "https://github.com/SIDDIQCCB/Masnavi-transcribing-work"

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_progress():
    p = Path(PROGRESS_FILE)
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except: pass
    return {}

def get_stats():
    p = Path(TRANSCRIPT_DIR)
    if not p.exists(): return 0, 0, 0
    docx = list(p.glob("*.docx"))
    txt  = list(p.glob("*.txt"))
    mb   = round(sum(f.stat().st_size for f in docx + txt) / 1_048_576, 1)
    return len(docx), len(txt), mb

def badge(status):
    styles = {
        "completed":  ("✓ Done",     "#00d68f", "rgba(0,214,143,.12)"),
        "pending":    ("⏳ Pending",  "#f5a623", "rgba(245,166,35,.12)"),
        "processing": ("⚙ Running",  "#60a5fa", "rgba(96,165,250,.12)"),
        "failed":     ("✗ Failed",   "#f87171", "rgba(248,113,113,.12)"),
    }
    lbl, col, bg = styles.get(status, (status, "#aaa", "rgba(0,0,0,.1)"))
    return (f'<span style="background:{bg};color:{col};padding:2px 10px;'
            f'border-radius:20px;font-size:.68rem;font-weight:800">{lbl}</span>')

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

:root {
  --bg:  #0e0f17; --c1: #151720; --c2: #1c1f2e;
  --c3:  #232638; --bd: #31364e; --gd: #f5a623;
  --gr:  #00d68f; --rd: #f87171; --bl: #60a5fa;
  --tx:  #eef0f8; --t2: #8890b0; --t3: #4e5470;
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif !important;
  background: var(--bg) !important;
  color: var(--tx) !important;
}
.main { background: var(--bg) !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
#MainMenu, footer { visibility: hidden !important; }
header { background: var(--bg) !important; border-bottom: 1px solid var(--bd) !important; }

[data-testid="collapsedControl"] {
  background: var(--gd) !important;
  border-radius: 0 10px 10px 0 !important;
  visibility: visible !important; opacity: 1 !important;
}
[data-testid="collapsedControl"] svg { fill: #000 !important; }

[data-testid="stSidebar"] {
  background: var(--c1) !important;
  border-right: 1px solid var(--bd) !important;
}
[data-testid="stSidebar"] > div { padding: 1.4rem 1.1rem !important; }
[data-testid="stSidebar"] * { color: var(--tx) !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input {
  background: var(--c2) !important; border: 1px solid var(--bd) !important;
  color: var(--tx) !important; border-radius: 10px !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] small,
[data-testid="stSidebar"] label { color: var(--t2) !important; font-size: .8rem !important; }
[data-testid="stSidebar"] hr { border-color: var(--bd) !important; margin: .75rem 0 !important; }

.stTabs [data-baseweb="tab-list"] {
  background: var(--c1) !important;
  border-bottom: 1px solid var(--bd) !important;
  border-radius: 0 !important; padding: 0 1.5rem !important; gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: var(--t2) !important;
  border-radius: 0 !important; font-weight: 500 !important;
  font-size: .83rem !important; padding: .9rem 1.4rem !important;
  border-bottom: 2px solid transparent !important; margin-bottom: -1px !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--tx) !important; }
.stTabs [aria-selected="true"] {
  background: transparent !important; color: var(--gd) !important;
  font-weight: 700 !important; border-bottom: 2px solid var(--gd) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

[data-testid="metric-container"] {
  background: var(--c1) !important; border: 1px solid var(--bd) !important;
  border-radius: 14px !important; padding: 1.2rem 1.4rem !important; transition: .2s !important;
}
[data-testid="metric-container"]:hover {
  border-color: var(--gd) !important; transform: translateY(-2px) !important;
}
[data-testid="metric-container"] label {
  color: var(--t3) !important; font-size: .65rem !important;
  font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: .12em !important;
}
[data-testid="metric-container"] [data-testid="metric-value"] {
  color: var(--tx) !important; font-size: 2rem !important; font-weight: 800 !important;
}

.stButton > button {
  background: linear-gradient(135deg, #f5a623, #e8920a) !important;
  color: #000 !important; border: none !important; border-radius: 12px !important;
  font-weight: 700 !important; font-size: .85rem !important; padding: .65rem 1.6rem !important;
  box-shadow: 0 4px 16px rgba(245,166,35,.3) !important; transition: .2s !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important; box-shadow: 0 8px 24px rgba(245,166,35,.45) !important;
}

.stProgress > div { background: var(--c3) !important; border-radius: 8px !important; height: 8px !important; }
.stProgress > div > div { background: linear-gradient(90deg,#f5a623,#ffc94a) !important; border-radius: 8px !important; }

.stTextInput > div > div > input {
  background: var(--c2) !important; border: 1px solid var(--bd) !important;
  border-radius: 10px !important; color: var(--tx) !important;
}
.stSelectbox > div > div {
  background: var(--c2) !important; border: 1px solid var(--bd) !important;
  border-radius: 10px !important; color: var(--tx) !important;
}
.streamlit-expanderHeader {
  background: var(--c2) !important; border-radius: 10px !important; color: var(--tx) !important;
}
.streamlit-expanderContent {
  background: var(--c1) !important; border: 1px solid var(--bd) !important;
  border-radius: 0 0 10px 10px !important;
}
[data-testid="stFileUploader"] {
  background: var(--c2) !important; border: 2px dashed var(--bd) !important;
  border-radius: 14px !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--gd) !important; }
[data-testid="stFileUploader"] * { color: var(--tx) !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--c1); }
::-webkit-scrollbar-thumb { background: var(--bd); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--gd); }
.stCaption, small { color: var(--t3) !important; }

/* Custom components */
.pg  { padding: 1.5rem 2rem; }
.sec { font-size:.65rem; font-weight:800; text-transform:uppercase;
       letter-spacing:.14em; color:var(--t3); padding: 1.3rem 0 .5rem; }
.info { background:var(--c2); border:1px solid var(--bd);
        border-left:3px solid var(--gd); border-radius:0 12px 12px 0;
        padding:.9rem 1.2rem; margin:.5rem 0;
        font-size:.84rem; line-height:1.75; color:var(--t2); }
.info b { color:var(--tx); }
.info code { background:var(--c3); color:var(--gd); padding:1px 6px;
             border-radius:5px; font-size:.76rem; }
.row { display:flex; align-items:center; gap:12px; padding:.65rem 1rem;
       border-bottom:1px solid var(--bd); transition:.12s; }
.row:hover { background:var(--c2); border-radius:8px; }
.row:last-child { border-bottom:none; }
.rn { color:var(--t3); min-width:26px; font-size:.7rem; font-weight:700; }
.rt { flex:1; color:var(--tx); font-size:.85rem; }
.rm { font-size:.7rem; color:var(--t3); white-space:nowrap; }
.step { background:var(--c1); border:1px solid var(--bd); border-radius:14px;
        padding:1rem 1.2rem; margin:.4rem 0;
        display:flex; gap:12px; align-items:flex-start; transition:.2s; }
.step:hover { border-color:var(--gd); }
.sn { width:30px; height:30px; flex-shrink:0; border-radius:50%;
      background:linear-gradient(135deg,#f5a623,#e8920a);
      display:flex; align-items:center; justify-content:center;
      font-weight:800; font-size:.82rem; color:#000; }
.st { font-weight:700; color:var(--tx); font-size:.88rem; margin-bottom:2px; }
.sd { color:var(--t2); font-size:.8rem; line-height:1.5; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:.2rem 0 .8rem'>
      <div style='font-size:1.35rem;font-weight:800;
           background:linear-gradient(135deg,#f5a623,#ffd166);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
        📜 Masnavi AI
      </div>
      <div style='font-size:.68rem;color:#4e5470;margin-top:2px'>
        Team Dashboard
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Folder settings
    st.markdown("**📁 Paths**")
    TRANSCRIPT_DIR = st.text_input(
        "Transcripts folder", TRANSCRIPT_DIR,
        label_visibility="collapsed",
        placeholder="transcripts/"
    )
    PROGRESS_FILE = st.text_input(
        "Progress file", PROGRESS_FILE,
        label_visibility="collapsed",
        placeholder="progress.json"
    )

    st.markdown("---")

    # Quick stats
    dcx, txn, mb = get_stats()
    data  = load_progress()
    vids  = data.get("videos", {}) if data else {}
    total = data.get("total", 0)   if data else 0
    done  = sum(1 for v in vids.values() if v["status"] == "completed")
    pct   = round(done / max(total, 1) * 100, 1)

    st.markdown(f"""
    <div style='background:#1c1f2e;border-radius:12px;padding:1rem'>
      <div style='font-size:.62rem;font-weight:800;text-transform:uppercase;
           letter-spacing:.12em;color:#4e5470;margin-bottom:.7rem'>Quick Stats</div>
      <div style='display:flex;justify-content:space-between;padding:.25rem 0'>
        <span style='font-size:.8rem;color:#8890b0'>Transcribed</span>
        <span style='font-weight:800;color:#00d68f'>{done}/{total}</span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.25rem 0'>
        <span style='font-size:.8rem;color:#8890b0'>DOCX files</span>
        <span style='font-weight:800;color:#a78bfa'>{dcx}</span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.25rem 0'>
        <span style='font-size:.8rem;color:#8890b0'>TXT files</span>
        <span style='font-weight:800;color:#60a5fa'>{txn}</span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.25rem 0'>
        <span style='font-size:.8rem;color:#8890b0'>Storage</span>
        <span style='font-weight:800;color:#f5a623'>{mb} MB</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # GitHub link
    st.markdown("**🔗 Links**")
    st.markdown(
        '<a href="https://github.com/SIDDIQCCB/Masnavi-transcribing-work"'
        ' target="_blank"'
        ' style="display:flex;align-items:center;gap:8px;background:#1c1f2e;'
        'border:1px solid #31364e;border-radius:8px;padding:8px 12px;'
        'text-decoration:none;color:#eef0f8;font-size:.8rem;font-weight:600">'
        '🐙&nbsp; GitHub Repository</a>',
        unsafe_allow_html=True
    )

# ── Top bar ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='display:flex;align-items:center;justify-content:space-between;
     padding:.9rem 2rem;background:#151720;border-bottom:1px solid #31364e'>
  <div style='display:flex;align-items:center;gap:12px'>
    <div style='width:40px;height:40px;border-radius:12px;
         background:linear-gradient(135deg,#f5a623,#e8920a);
         display:flex;align-items:center;justify-content:center;font-size:1.2rem;
         box-shadow:0 4px 14px rgba(245,166,35,.35)'>📜</div>
    <div>
      <div style='font-size:1.1rem;font-weight:800;color:#eef0f8'>Masnavi AI</div>
      <div style='font-size:.71rem;color:#4e5470;
           font-family:"Noto Nastaliq Urdu",serif;direction:rtl'>
        مثنوی مولانا روم — ٹیم ڈیش بورڈ
      </div>
    </div>
  </div>
  <div style='font-size:.75rem;color:#8890b0;background:#1c1f2e;
       border:1px solid #31364e;border-radius:8px;padding:5px 12px'>
    📊 Team Dashboard — Read Only
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊  Dashboard", "📂  Files", "❓  Help"])

# ═════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="pg">', unsafe_allow_html=True)

    data  = load_progress()
    vids  = data.get("videos", {}) if data else {}
    total = data.get("total", 0)   if data else 0
    done  = sum(1 for v in vids.values() if v["status"] == "completed")
    pend  = sum(1 for v in vids.values() if v["status"] == "pending")
    fail  = sum(1 for v in vids.values() if v["status"] == "failed")
    proc  = sum(1 for v in vids.values() if v["status"] == "processing")
    pct   = round(done / max(total, 1) * 100, 1)
    dcx, txn, mb = get_stats()

    # ── Metrics ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📹 Total",      total or "—")
    c2.metric("✅ Transcribed", done)
    c3.metric("✎ Corrected",  dcx,
              help="DOCX files in transcripts folder")
    c4.metric("⏳ Pending",    pend)
    c5.metric("⚙ Running",    proc)
    c6.metric("❌ Failed",     fail)

    # ── Progress bar ──────────────────────────────────────────────────────
    if total > 0:
        st.markdown("")
        st.progress(pct / 100)
        l, r = st.columns(2)
        l.caption(f"{pct}% of playlist transcribed")
        r.caption(f"{done} done · {pend} remaining · {total} total")

    # ── Corrected DOCX files ──────────────────────────────────────────────
    docx_files = sorted(
        Path(TRANSCRIPT_DIR).glob("*.docx"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(TRANSCRIPT_DIR).exists() else []

    st.markdown('<div class="sec">✎ Corrected Files</div>', unsafe_allow_html=True)

    if docx_files:
        st.markdown(
            f'<div class="info"><b>{len(docx_files)} corrected DOCX files</b>'
            f' in <code>{TRANSCRIPT_DIR}/</code> — ready for InPage.</div>',
            unsafe_allow_html=True
        )
        with st.expander(f"View all {len(docx_files)} corrected files"):
            for i, f in enumerate(docx_files, 1):
                mtime = datetime.fromtimestamp(
                    f.stat().st_mtime).strftime("%d/%m/%Y")
                kb = f.stat().st_size // 1024
                st.markdown(
                    f'<div class="row">'
                    f'<span class="rn">#{i}</span>'
                    f'<span class="rt">{f.stem[:60]}</span>'
                    f'<span style="background:rgba(167,139,250,.12);color:#a78bfa;'
                    f'padding:2px 9px;border-radius:20px;font-size:.68rem;font-weight:800">'
                    f'✎ Corrected</span>'
                    f'<span class="rm">{mtime} · {kb}KB</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            '<div class="info">No corrected files yet.</div>',
            unsafe_allow_html=True
        )

    # ── Video status list ─────────────────────────────────────────────────
    if vids:
        st.markdown(
            '<div class="sec">🎬 Video Status</div>',
            unsafe_allow_html=True
        )
        f1, f2 = st.columns([2, 3])
        with f1:
            flt = st.selectbox(
                "Filter", ["all", "completed", "pending", "failed", "processing"],
                key="df", label_visibility="collapsed"
            )
        with f2:
            srch = st.text_input(
                "Search", "", placeholder="Search title…",
                key="ds", label_visibility="collapsed"
            )

        rows = ""
        shown = 0
        for i, (vid_id, info) in enumerate(vids.items(), 1):
            if flt != "all" and info["status"] != flt:
                continue
            title = info.get("title", vid_id)
            if srch and srch.lower() not in title.lower():
                continue
            shown += 1
            ts = (datetime.fromtimestamp(info["completed_at"])
                  .strftime("%d/%m %H:%M")
                  if info.get("completed_at") else "")
            doc = '<span style="color:#00d68f;font-size:.72rem">📄</span>' \
                  if info.get("transcript_path") else ""
            rows += (
                f'<div class="row">'
                f'<span class="rn">#{i}</span>'
                f'<span class="rt">{title[:65]}</span>'
                f'{badge(info["status"])} {doc}'
                f'<span class="rm">{ts}</span>'
                f'</div>'
            )

        if rows:
            st.markdown(rows, unsafe_allow_html=True)
        else:
            st.caption("No videos match.")

    elif not docx_files:
        st.markdown(
            '<div class="info" style="margin-top:1rem">'
            'No transcription data yet. Run transcription on your '
            'local PC first, then push <code>progress.json</code> '
            'and the <code>transcripts/</code> folder to GitHub.</div>',
            unsafe_allow_html=True
        )

    # Refresh
    _, rb = st.columns([9, 1])
    with rb:
        if st.button("↺", key="ref", help="Refresh dashboard"):
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
# TAB 2 — FILES
# ═════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="pg">', unsafe_allow_html=True)
    st.markdown('<div class="sec">📂 Transcript Files</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info">Download DOCX → correct errors in Word → '
        'copy text → paste into InPage for printing.</div>',
        unsafe_allow_html=True
    )

    docx_list = sorted(
        Path(TRANSCRIPT_DIR).glob("*.docx"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(TRANSCRIPT_DIR).exists() else []

    txt_list = sorted(
        Path(TRANSCRIPT_DIR).glob("*.txt"),
        key=lambda f: f.stat().st_mtime, reverse=True
    ) if Path(TRANSCRIPT_DIR).exists() else []

    if not docx_list and not txt_list:
        st.markdown(
            f'<div class="info">No files found in <code>{TRANSCRIPT_DIR}/</code>.<br>'
            f'Run transcription on your local PC, then push files to GitHub.</div>',
            unsafe_allow_html=True
        )
    else:
        m1, m2, m3 = st.columns(3)
        total_mb = round(
            sum(f.stat().st_size for f in docx_list + txt_list) / 1_048_576, 1
        )
        m1.metric("📝 DOCX Files", len(docx_list))
        m2.metric("📄 TXT Files",  len(txt_list))
        m3.metric("💾 Total Size", f"{total_mb} MB")

        st.markdown("")
        t1, t2 = st.tabs(["📝 DOCX — Edit & Print", "📄 TXT — Database"])

        with t1:
            if not docx_list:
                st.caption("No DOCX files yet.")
            else:
                sd = st.text_input(
                    "Search", "", placeholder="Filter files…",
                    key="fsd", label_visibility="collapsed"
                )
                for f in docx_list:
                    if sd and sd.lower() not in f.stem.lower():
                        continue
                    mtime = datetime.fromtimestamp(
                        f.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                    kb = f.stat().st_size // 1024
                    nc, ic, bc = st.columns([4, 2, 1])
                    with nc:
                        st.markdown(
                            f'<div style="padding:.3rem 0;font-size:.84rem">'
                            f'📝 {f.stem[:55]}</div>',
                            unsafe_allow_html=True
                        )
                    with ic:
                        st.markdown(
                            f'<div style="padding:.35rem 0;font-size:.71rem;color:#4e5470">'
                            f'{kb}KB · {mtime}</div>',
                            unsafe_allow_html=True
                        )
                    with bc:
                        st.download_button(
                            "⬇",
                            data=f.read_bytes(),
                            file_name=f.name,
                            mime="application/vnd.openxmlformats-officedocument"
                                 ".wordprocessingml.document",
                            key=f"dl_{f.name}",
                            use_container_width=True
                        )

        with t2:
            if not txt_list:
                st.caption("No TXT files yet.")
            else:
                sel = st.selectbox(
                    "Select file",
                    [f.name for f in txt_list],
                    key="tp", label_visibility="collapsed"
                )
                if sel:
                    fp      = Path(TRANSCRIPT_DIR) / sel
                    content = fp.read_text(encoding="utf-8")
                    rc, dc  = st.columns([4, 1])
                    with rc:
                        st.caption(f"{len(content):,} characters")
                    with dc:
                        st.download_button(
                            "⬇ Download",
                            content.encode("utf-8"),
                            file_name=sel,
                            mime="text/plain; charset=utf-8",
                            key="tdl"
                        )
                    st.code(content[:2000], language=None)

    st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
# TAB 3 — HELP
# ═════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="pg">', unsafe_allow_html=True)

    st.markdown('<div class="sec">How This Works</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info">
    <b>This online app is the Team Dashboard only.</b><br>
    Transcription runs on the local PC. The app shows progress
    and lets team members download files.<br><br>
    <b>Transcription runs on local PC:</b><br>
    <code>python run_transcription.py --url "URL" --model medium --threads 4</code>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec">Team Workflow</div>', unsafe_allow_html=True)
    for num, title, desc in [
        ("1", "Run transcription",
         "On your local PC: python run_transcription.py --url ..."),
        ("2", "Push to GitHub",
         "git add . && git commit -m 'update' && git push"),
        ("3", "Team sees progress",
         "Dashboard refreshes and shows all videos with status"),
        ("4", "Download DOCX",
         "Any team member downloads DOCX from Files tab"),
        ("5", "Correct in Word",
         "Open DOCX in Microsoft Word, fix errors, save"),
        ("6", "Paste into InPage",
         "Copy corrected text → paste into InPage → format for printing"),
    ]:
        st.markdown(
            f'<div class="step">'
            f'<div class="sn">{num}</div>'
            f'<div><div class="st">{title}</div>'
            f'<div class="sd">{desc}</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="sec">Fix 403 Download Error</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info">
    If you see <b>HTTP 403 Forbidden</b> when transcribing locally:<br>
    <code>pip install --upgrade yt-dlp</code><br>
    Run this in terminal then try again.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec">Important Notes</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info">
    <b>Model:</b> Always use <code>medium</code> for best Urdu/Persian accuracy<br>
    <b>CPU Threads:</b> Keep at 4 — your i5-4570 has exactly 4 cores<br>
    <b>GitHub Repo:</b>
    <a href="https://github.com/SIDDIQCCB/Masnavi-transcribing-work"
       target="_blank" style="color:#f5a623">
       github.com/SIDDIQCCB/Masnavi-transcribing-work
    </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
