"""
Masnavi AI — Transcription System
Run: streamlit run app.py
"""
import streamlit as st
import json, os, sys, re, time, subprocess
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Masnavi AI",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROGRESS_FILE  = "progress.json"
TRANSCRIPT_DIR = "transcripts"
AUDIO_DIR      = "audio_cache"
LOG_FILE       = "transcription.log"
PID_FILE       = "transcription.pid"

for k,v in {"videos":[],"playlist_url":""}.items():
    if k not in st.session_state: st.session_state[k]=v

def load_progress():
    p=Path(PROGRESS_FILE)
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except: pass
    return {}

def _project_dir():
    return Path(__file__).parent.resolve()

def is_running():
    pid_path = _project_dir() / PID_FILE
    if not pid_path.exists(): return False
    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, 0)
        return True
    except: return False

def log_tail(n=35):
    lf = _project_dir() / LOG_FILE
    if not lf.exists(): return ""
    try:
        lines = lf.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-n:])
    except: return ""

def live_pct():
    m=re.findall(r'(\d+\.?\d*)%',log_tail(5))
    return float(m[-1]) if m else None

def live_stage():
    for ln in reversed(log_tail(8).splitlines()):
        for s in ["Downloading","Transcribing","Loading","Saving"]:
            if s.lower() in ln.lower(): return s
    return "Working"

def live_video():
    for ln in reversed(log_tail(12).splitlines()):
        m=re.search(r'Processing:\s*(.+)',ln)
        if m: return m.group(1).strip()
    return ""

def folder_stats():
    p=Path(TRANSCRIPT_DIR)
    if not p.exists(): return 0,0,0
    d=list(p.glob("*.docx")); t=list(p.glob("*.txt"))
    mb=round(sum(f.stat().st_size for f in d+t)/1_048_576,1)
    return len(d),len(t),mb

def badge(s):
    M={"completed":("✓","#00d68f","rgba(0,214,143,.1)"),
       "pending":("⏳","#f5a623","rgba(245,166,35,.1)"),
       "processing":("⚙","#60a5fa","rgba(96,165,250,.1)"),
       "failed":("✗","#f87171","rgba(248,113,113,.1)")}
    lbl,col,bg=M.get(s,(s,"#aaa","rgba(0,0,0,.1)"))
    return (f'<span style="background:{bg};color:{col};padding:2px 10px;'
            f'border-radius:20px;font-size:.68rem;font-weight:800;'
            f'letter-spacing:.04em">{lbl}</span>')

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

:root{
  --bg:#0e0f17;
  --c1:#151720;
  --c2:#1c1f2e;
  --c3:#232638;
  --c4:#2b2f45;
  --bd:#31364e;
  --gd:#f5a623;
  --gd2:#ffc94a;
  --gr:#00d68f;
  --rd:#f87171;
  --bl:#60a5fa;
  --tx:#eef0f8;
  --t2:#8890b0;
  --t3:#4e5470;
  --ur:'Noto Nastaliq Urdu',serif;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;background:var(--bg)!important;color:var(--tx)!important}
.main{background:var(--bg)!important}
.block-container{padding:0!important;max-width:100%!important}

/* Chrome */
#MainMenu,footer{visibility:hidden!important}
header{background:var(--bg)!important;border-bottom:1px solid var(--bd)!important}

/* Sidebar toggle pill */
[data-testid="collapsedControl"]{
  background:var(--gd)!important;border-radius:0 10px 10px 0!important;
  visibility:visible!important;opacity:1!important;
}
[data-testid="collapsedControl"] svg{fill:#000!important}

/* Sidebar */
[data-testid="stSidebar"]{background:var(--c1)!important;border-right:1px solid var(--bd)!important}
[data-testid="stSidebar"]>div{padding:1.4rem 1.1rem!important}
[data-testid="stSidebar"] *{color:var(--tx)!important}
[data-testid="stSidebar"] .stSelectbox>div>div,
[data-testid="stSidebar"] .stTextInput>div>div>input{
  background:var(--c2)!important;border:1px solid var(--bd)!important;
  color:var(--tx)!important;border-radius:10px!important;font-size:.82rem!important
}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] small,
[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:var(--t2)!important;font-size:.8rem!important}
[data-testid="stSidebar"] hr{border-color:var(--bd)!important;margin:.75rem 0!important}

/* Tabs - app nav bar */
.stTabs [data-baseweb="tab-list"]{
  background:var(--c1)!important;border-bottom:1px solid var(--bd)!important;
  border-radius:0!important;padding:0 1.5rem!important;gap:0!important
}
.stTabs [data-baseweb="tab"]{
  background:transparent!important;color:var(--t2)!important;
  border-radius:0!important;font-weight:500!important;font-size:.83rem!important;
  padding:.9rem 1.4rem!important;border-bottom:2px solid transparent!important;
  margin-bottom:-1px!important;letter-spacing:.01em!important
}
.stTabs [data-baseweb="tab"]:hover{color:var(--tx)!important}
.stTabs [aria-selected="true"]{
  background:transparent!important;color:var(--gd)!important;
  font-weight:700!important;border-bottom:2px solid var(--gd)!important
}
.stTabs [data-baseweb="tab-panel"]{padding:0!important}

/* Metrics */
[data-testid="metric-container"]{
  background:var(--c1)!important;border:1px solid var(--bd)!important;
  border-radius:14px!important;padding:1.2rem 1.4rem!important;transition:.2s!important
}
[data-testid="metric-container"]:hover{border-color:var(--gd)!important;transform:translateY(-2px)!important}
[data-testid="metric-container"] label{color:var(--t3)!important;font-size:.65rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:.12em!important}
[data-testid="metric-container"] [data-testid="metric-value"]{color:var(--tx)!important;font-size:2rem!important;font-weight:800!important}

/* Buttons */
.stButton>button{
  background:linear-gradient(135deg,#f5a623,#e8920a)!important;
  color:#000!important;border:none!important;border-radius:12px!important;
  font-weight:700!important;font-size:.85rem!important;padding:.65rem 1.6rem!important;
  box-shadow:0 4px 16px rgba(245,166,35,.3)!important;transition:.2s!important;
  font-family:'DM Sans',sans-serif!important;letter-spacing:.01em!important
}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 24px rgba(245,166,35,.45)!important}
.stButton>button:disabled{background:var(--c3)!important;color:var(--t3)!important;box-shadow:none!important;transform:none!important}

/* Progress */
.stProgress>div{background:var(--c3)!important;border-radius:8px!important;height:8px!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--gd),var(--gd2))!important;border-radius:8px!important}

/* Inputs */
.stTextInput>div>div>input,.stSelectbox>div>div{
  background:var(--c2)!important;border:1px solid var(--bd)!important;
  border-radius:10px!important;color:var(--tx)!important;font-size:.86rem!important
}
.stTextInput>div>div>input:focus{border-color:var(--gd)!important;box-shadow:0 0 0 3px rgba(245,166,35,.15)!important}
.stRadio label{color:var(--tx)!important;font-size:.84rem!important}
.stRadio>div{gap:8px!important}

/* Expander */
.streamlit-expanderHeader{background:var(--c2)!important;border-radius:10px!important;color:var(--tx)!important}
.streamlit-expanderContent{background:var(--c1)!important;border:1px solid var(--bd)!important;border-radius:0 0 10px 10px!important}

/* Upload */
[data-testid="stFileUploader"]{background:var(--c2)!important;border:2px dashed var(--bd)!important;border-radius:14px!important}
[data-testid="stFileUploader"]:hover{border-color:var(--gd)!important}
[data-testid="stFileUploader"] *{color:var(--tx)!important}

/* Scrollbar */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--c1)}
::-webkit-scrollbar-thumb{background:var(--bd);border-radius:2px}
::-webkit-scrollbar-thumb:hover{background:var(--gd)}
.stCaption,small{color:var(--t3)!important;font-size:.75rem!important}

/* ── Custom components ── */
.pg{padding:1.5rem 2rem}

/* App top bar */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:.9rem 2rem;background:var(--c1);border-bottom:1px solid var(--bd)
}
.brand{display:flex;align-items:center;gap:12px}
.brand-icon{
  width:40px;height:40px;border-radius:12px;
  background:linear-gradient(135deg,#f5a623,#e8920a);
  display:flex;align-items:center;justify-content:center;
  font-size:1.2rem;box-shadow:0 4px 14px rgba(245,166,35,.35);flex-shrink:0
}
.brand-name{font-size:1.1rem;font-weight:800;color:var(--tx);letter-spacing:-.02em}
.brand-sub{font-size:.71rem;color:var(--t3);margin-top:1px;font-family:var(--ur);direction:rtl}

/* Status */
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.dot-live{width:7px;height:7px;border-radius:50%;background:var(--gr);display:inline-block;animation:blink 1.4s infinite}
.pill{display:inline-flex;align-items:center;gap:6px;padding:4px 13px;border-radius:20px;font-size:.75rem;font-weight:700}
.pill-on{background:rgba(0,214,143,.1);color:var(--gr);border:1px solid rgba(0,214,143,.25)}
.pill-off{background:var(--c2);color:var(--t3);border:1px solid var(--bd)}

/* Section label */
.sec{font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.14em;color:var(--t3);padding:1.3rem 0 .5rem}

/* Cards */
.card{background:var(--c1);border:1px solid var(--bd);border-radius:14px;padding:1.2rem 1.4rem;margin:.4rem 0;transition:.2s}
.card:hover{border-color:var(--gd)}

/* Info */
.info{background:var(--c2);border:1px solid var(--bd);border-left:3px solid var(--gd);
      border-radius:0 12px 12px 0;padding:.9rem 1.2rem;margin:.5rem 0;
      font-size:.84rem;line-height:1.75;color:var(--t2)}
.info b{color:var(--tx)}
.info code{background:var(--c3);color:var(--gd);padding:1px 6px;border-radius:5px;font-family:'DM Mono',monospace;font-size:.76rem}

/* Live progress card */
.livebox{
  background:var(--c1);border:1px solid var(--gd);border-radius:14px;
  padding:1.3rem 1.5rem;margin:.8rem 0;
  box-shadow:0 0 0 1px rgba(245,166,35,.08),0 8px 32px rgba(0,0,0,.4)
}
.lv-head{display:flex;align-items:center;gap:8px;margin-bottom:.9rem}
.lv-tag{font-size:.7rem;font-weight:800;letter-spacing:.08em;color:var(--gr)}
.lv-video{font-size:.95rem;font-weight:700;color:var(--tx);margin-bottom:.3rem;line-height:1.3}
.lv-stage{font-size:.75rem;color:var(--t2);margin-bottom:.8rem}

/* Row */
.row{display:flex;align-items:center;gap:12px;padding:.65rem 1rem;border-bottom:1px solid var(--bd);transition:.12s}
.row:hover{background:var(--c2);border-radius:8px}
.row:last-child{border-bottom:none}
.rn{color:var(--t3);min-width:26px;font-size:.7rem;font-weight:700}
.rt{flex:1;color:var(--tx);font-size:.85rem}
.rm{font-size:.7rem;color:var(--t3);white-space:nowrap}

/* Log */
.logbox{
  background:#080a12;border:1px solid var(--bd);border-radius:12px;
  color:#00d68f;font-family:'DM Mono',monospace;font-size:.71rem;
  line-height:1.75;padding:1rem 1.2rem;max-height:210px;overflow-y:auto;white-space:pre-wrap
}

/* Step */
.step{background:var(--c1);border:1px solid var(--bd);border-radius:14px;
      padding:1rem 1.2rem;margin:.4rem 0;display:flex;gap:12px;align-items:flex-start;transition:.2s}
.step:hover{border-color:var(--gd)}
.sn{width:30px;height:30px;flex-shrink:0;border-radius:50%;background:linear-gradient(135deg,#f5a623,#e8920a);
    display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.82rem;color:#000;
    box-shadow:0 2px 8px rgba(245,166,35,.3)}
.st{font-weight:700;color:var(--tx);font-size:.88rem;margin-bottom:2px}
.sd{color:var(--t2);font-size:.8rem;line-height:1.5}

/* Correction */
.cr{display:flex;align-items:center;gap:8px;padding:.55rem .8rem;border-bottom:1px solid var(--bd)}
.cr:last-child{border-bottom:none}
.cw{flex:1;color:#f87171;font-family:var(--ur);direction:rtl;text-align:right;font-size:.88rem}
.cc{flex:1;color:#00d68f;font-family:var(--ur);direction:rtl;text-align:right;font-size:.88rem}
.cn{color:var(--t3);font-size:.7rem;min-width:32px;text-align:right;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:.2rem 0 .8rem'>
      <div style='font-size:1.35rem;font-weight:800;background:linear-gradient(135deg,#f5a623,#ffd166);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent'>📜 Masnavi AI</div>
      <div style='font-size:.68rem;color:#4e5470;margin-top:2px'>Transcription System v2</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**🎙 Model**")
    model_size = st.selectbox("m",["tiny","base","small","medium","large-v2"],index=3,
                               label_visibility="collapsed")
    captions={"tiny":"⚡⚡⚡⚡ Very fast, lower accuracy",
               "base":"⚡⚡⚡ Fast",
               "small":"⚡⚡ Balanced",
               "medium":"⚡ Best for Urdu/Persian ✓",
               "large-v2":"🐢 Most accurate"}
    st.caption(captions.get(model_size,""))

    st.markdown("**🖥 CPU Threads**")
    cpu_threads=st.slider("t",1,4,4,label_visibility="collapsed",
                           help="i5-4570 = 4 cores. Always keep at 4.")
    st.caption(f"{cpu_threads}/4 cores  (i5-4570)")

    st.markdown("**🌐 Language**")
    language=st.selectbox("l",["auto (Urdu+Persian+English)","ur — Urdu","fa — Persian"],
                           index=0,label_visibility="collapsed")
    lang_code=None if "auto" in language else language[:2]

    st.markdown("---")
    st.markdown("**📁 Folders**")
    out_dir   = st.text_input("o",TRANSCRIPT_DIR,label_visibility="collapsed",placeholder="transcripts/")
    audio_dir = st.text_input("a",AUDIO_DIR,      label_visibility="collapsed",placeholder="audio_cache/")
    prog_file = st.text_input("p",PROGRESS_FILE,  label_visibility="collapsed",placeholder="progress.json")

    st.markdown("---")
    st.markdown("**🔗 Links**")
    st.markdown("""
    <div style='display:flex;flex-direction:column;gap:6px;margin-top:.3rem'>
      <a href='https://github.com' target='_blank'
         style='display:flex;align-items:center;gap:8px;background:var(--c2);
                border:1px solid var(--bd);border-radius:8px;padding:7px 12px;
                text-decoration:none;color:var(--tx);font-size:.8rem;font-weight:600;
                transition:.2s' onmouseover="this.style.borderColor='#f5a623'"
                onmouseout="this.style.borderColor='var(--bd)'">
        <span style='font-size:1rem'>🐙</span> GitHub Repository
      </a>
    </div>
    """, unsafe_allow_html=True)
    run=is_running()
    st.markdown(f"""
    <div style='background:var(--c2);border-radius:12px;padding:1rem'>
      <div style='font-size:.62rem;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--t3);margin-bottom:.6rem'>Quick Stats</div>
      <div style='display:flex;justify-content:space-between;padding:.2rem 0'>
        <span style='font-size:.8rem;color:var(--t2)'>Status</span>
        <span class="pill {'pill-on' if run else 'pill-off'}">
          {'<span class="dot-live"></span> Live' if run else '● Idle'}
        </span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.2rem 0'>
        <span style='font-size:.8rem;color:var(--t2)'>DOCX files</span>
        <span style='font-weight:800;color:#a78bfa'>{dcx}</span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.2rem 0'>
        <span style='font-size:.8rem;color:var(--t2)'>TXT files</span>
        <span style='font-weight:800;color:var(--bl)'>{txn}</span>
      </div>
      <div style='display:flex;justify-content:space-between;padding:.2rem 0'>
        <span style='font-size:.8rem;color:var(--t2)'>Storage</span>
        <span style='font-weight:800;color:var(--gd)'>{mb} MB</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────────────────────────────────
run=is_running()
st.markdown(f"""
<div class="topbar">
  <div class="brand">
    <div class="brand-icon">📜</div>
    <div>
      <div class="brand-name">Masnavi AI</div>
      <div class="brand-sub">مثنوی مولانا روم — ٹرانسکرپشن سسٹم</div>
    </div>
  </div>
  <span class="pill {'pill-on' if run else 'pill-off'}">
    {'<span class="dot-live"></span>&nbsp;Transcribing' if run else '● Idle'}
  </span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5=st.tabs([
    "📊  Dashboard","🎬  Transcribe","📂  Files","🧠  Learn","❓  Help"
])

# ═════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════
with tab1:
    with st.container():
        st.markdown('<div class="pg">',unsafe_allow_html=True)
        data=load_progress()
        vids=data.get("videos",{}) if data else {}
        total=data.get("total",0) if data else 0
        done=sum(1 for v in vids.values() if v["status"]=="completed")
        pend=sum(1 for v in vids.values() if v["status"]=="pending")
        fail=sum(1 for v in vids.values() if v["status"]=="failed")
        pct=round(done/max(total,1)*100,1)
        dcx,txn,mb=folder_stats()

        # Metrics
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📹 Total",total or "—")
        c2.metric("✅ Done",done)
        c3.metric("✎ Corrected",dcx)
        c4.metric("⏳ Pending",pend)
        c5.metric("❌ Failed",fail)

        if total>0:
            st.markdown("")
            st.progress(pct/100)
            l,r=st.columns(2)
            l.caption(f"{pct}% of playlist transcribed")
            r.caption(f"{done} done · {pend} remaining · {total} total")

        # ── Live progress ──────────────────────────────────────────────
        run=is_running()
        if run:
            log=log_tail(15)
            pct_v=live_pct(); stage=live_stage(); vid=live_video()
            st.markdown(f"""
            <div class="livebox">
              <div class="lv-head">
                <span class="dot-live"></span>
                <span class="lv-tag">LIVE — TRANSCRIBING NOW</span>
              </div>
              <div class="lv-video">{vid[:80] or "Processing…"}</div>
              <div class="lv-stage">⚙ {stage}{"…" if stage else ""}</div>
            </div>
            """,unsafe_allow_html=True)
            if pct_v is not None:
                st.progress(pct_v/100,text=f"{stage} — {pct_v:.1f}%")
            safe=log.replace("<","&lt;").replace(">","&gt;")
            st.markdown(f'<div class="logbox">{safe}</div>',unsafe_allow_html=True)
            time.sleep(4); st.rerun()

        # ── Corrected files ────────────────────────────────────────────
        docx_files=sorted(Path(out_dir).glob("*.docx"),
                           key=lambda f:f.stat().st_mtime,reverse=True) \
                   if Path(out_dir).exists() else []
        st.markdown('<div class="sec">✎ Corrected Files</div>',unsafe_allow_html=True)
        if docx_files:
            st.markdown(f'<div class="info"><b>{len(docx_files)} corrected files</b> in <code>{out_dir}/</code></div>',unsafe_allow_html=True)
            with st.expander(f"View all {len(docx_files)} files"):
                for i,f in enumerate(docx_files,1):
                    mtime=datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%y")
                    kb=f.stat().st_size//1024
                    st.markdown(f'<div class="row"><span class="rn">#{i}</span><span class="rt">{f.stem[:55]}</span><span style="background:rgba(167,139,250,.1);color:#a78bfa;padding:2px 9px;border-radius:20px;font-size:.68rem;font-weight:800">✎</span><span class="rm">{mtime}·{kb}K</span></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="info">No corrected files yet.</div>',unsafe_allow_html=True)

        # ── Video list ─────────────────────────────────────────────────
        if vids:
            st.markdown('<div class="sec">🎬 Video Status</div>',unsafe_allow_html=True)
            f1,f2=st.columns([2,3])
            with f1: flt=st.selectbox("",["all","completed","pending","failed"],key="df",label_visibility="collapsed")
            with f2: srch=st.text_input("","",placeholder="Search…",key="ds",label_visibility="collapsed")
            rows=""
            for i,(vid_id,info) in enumerate(vids.items(),1):
                if flt!="all" and info["status"]!=flt: continue
                t=info.get("title",vid_id)
                if srch and srch.lower() not in t.lower(): continue
                ts=datetime.fromtimestamp(info["completed_at"]).strftime("%d/%m %H:%M") if info.get("completed_at") else ""
                rows+=(f'<div class="row"><span class="rn">#{i}</span>'
                       f'<span class="rt">{t[:65]}</span>'
                       f'{badge(info["status"])}'
                       f'<span class="rm">{ts}</span></div>')
            if rows: st.markdown(rows,unsafe_allow_html=True)

        # ── Last log (when idle) ───────────────────────────────────────
        if not run:
            log=log_tail(20)
            if log.strip():
                st.markdown('<div class="sec">📋 Last Session Log</div>',unsafe_allow_html=True)
                safe=log.replace("<","&lt;").replace(">","&gt;")
                st.markdown(f'<div class="logbox">{safe}</div>',unsafe_allow_html=True)

        _,rb=st.columns([9,1])
        with rb:
            if st.button("↺",key="ref",help="Refresh"): st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════
# TRANSCRIBE
# ═════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="pg">',unsafe_allow_html=True)
    run=is_running()

    if run:
        st.markdown('<div class="info">⚙ Transcription is running. Wait for it to finish before starting a new job.</div>',unsafe_allow_html=True)
    
    left,right=st.columns([3,2])
    with left:
        st.markdown('<div class="sec">🎬 New Transcription Job</div>',unsafe_allow_html=True)
        job_type=st.radio("Type",["Single Video","Full Playlist"],horizontal=True)
        url_input=st.text_input("YouTube URL","",
            placeholder="https://youtu.be/...  or  youtube.com/playlist?list=...")
        ca,cb,_=st.columns([2,2,3])
        with ca: fetch=st.button("🔍 Fetch",use_container_width=True,disabled=run)
        with cb: start=st.button("▶ Start",use_container_width=True,
                                  disabled=not st.session_state.videos or run)

        if fetch:
            if not url_input.strip(): st.error("Enter a URL.")
            else:
                with st.spinner("Fetching…"):
                    try:
                        if job_type=="Full Playlist":
                            from transcriber import get_playlist_videos
                            vs=get_playlist_videos(url_input.strip())
                        else:
                            from transcriber import get_video_title
                            t=get_video_title(url_input.strip()) or "Video"
                            vs=[{"id":"single","url":url_input.strip(),"title":t}]
                        st.session_state.videos=vs
                        st.session_state.playlist_url=url_input.strip()
                        st.success(f"✓ Found {len(vs)} video(s)")
                    except Exception as e: st.error(f"Error: {e}")

        if start and st.session_state.videos and not run:
            flag="--playlist" if job_type=="Full Playlist" else "--url"

            # Use absolute paths — fixes "file not found" issue
            script_dir  = Path(__file__).parent.resolve()
            script_path = script_dir / "run_transcription.py"

            if not script_path.exists():
                st.error(f"❌ Cannot find run_transcription.py in:\n`{script_dir}`\n\nMake sure all project files are in the same folder.")
            else:
                cmd=[sys.executable,
                     "-u",              # ← CRITICAL: unbuffered output
                                        # Without this, Python holds all output
                                        # in memory and never writes to log file
                                        # until buffer fills (8KB) — causes 0% forever
                     str(script_path),
                     flag, st.session_state.playlist_url,
                     "--model",     model_size,
                     "--threads",   str(cpu_threads),
                     "--output",    str(script_dir / out_dir),
                     "--audio-dir", str(script_dir / audio_dir),
                     "--progress",  str(script_dir / prog_file)]
                if lang_code: cmd+=["--language", lang_code]

                log_path = script_dir / LOG_FILE
                pid_path = script_dir / PID_FILE

                try:
                    log_path = script_dir / LOG_FILE
                    pid_path = script_dir / PID_FILE
                    logf = open(str(log_path), "w", encoding="utf-8", buffering=1)  # line-buffered
                    env  = os.environ.copy()
                    env["PYTHONUNBUFFERED"] = "1"  # force unbuffered output
                    proc = subprocess.Popen(
                        cmd, stdout=logf, stderr=logf,
                        cwd=str(script_dir), env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
                    pid_path.write_text(str(proc.pid))
                    st.success(f"✅ Started! (PID {proc.pid}) — Switch to **Dashboard** to watch live progress.")
                    time.sleep(2)
                    st.rerun()
                except FileNotFoundError:
                    st.error("❌ Python not found. Activate your virtual environment first:\n`.venv\\Scripts\\activate`")
                except Exception as e:
                    st.error(f"❌ Failed to start: {e}")

    with right:
        if st.session_state.videos:
            st.markdown(f'<div class="info"><b>{len(st.session_state.videos)}</b> videos ready</div>',unsafe_allow_html=True)
            for i,v in enumerate(st.session_state.videos[:10],1):
                st.markdown(f'<div class="row"><span class="rn">#{i}</span><span class="rt">{v["title"][:50]}</span></div>',unsafe_allow_html=True)
            if len(st.session_state.videos)>10:
                st.caption(f"… and {len(st.session_state.videos)-10} more")
        else:
            st.markdown("""<div class="info"><b>Steps:</b><br>
            1. Paste YouTube URL<br>2. Click Fetch<br>
            3. Click Start<br>4. Watch live in Dashboard</div>""",unsafe_allow_html=True)
            st.markdown("""<div class="info" style="margin-top:.5rem"><b>⚠ If download fails (403):</b><br>
            Run in terminal:<br><code>pip install --upgrade yt-dlp</code><br>
            Then try again.</div>""",unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════
# FILES
# ═════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="pg">',unsafe_allow_html=True)
    st.markdown('<div class="sec">📂 Transcript Files</div>',unsafe_allow_html=True)
    st.markdown('<div class="info">Download DOCX → correct in Word → copy text → paste into InPage for book printing.</div>',unsafe_allow_html=True)

    docx_list=sorted(Path(out_dir).glob("*.docx"),key=lambda f:f.stat().st_mtime,reverse=True) if Path(out_dir).exists() else []
    txt_list= sorted(Path(out_dir).glob("*.txt"), key=lambda f:f.stat().st_mtime,reverse=True) if Path(out_dir).exists() else []

    if not docx_list and not txt_list:
        st.markdown(f'<div class="info">No files in <code>{out_dir}/</code> yet.</div>',unsafe_allow_html=True)
    else:
        m1,m2,m3=st.columns(3)
        tot_mb=round(sum(f.stat().st_size for f in docx_list+txt_list)/1_048_576,1)
        m1.metric("📝 DOCX",len(docx_list))
        m2.metric("📄 TXT",len(txt_list))
        m3.metric("💾 MB",tot_mb)
        st.markdown("")
        t1,t2=st.tabs(["📝 DOCX — Edit & Print","📄 TXT — Database"])
        with t1:
            if not docx_list: st.caption("No DOCX files yet.")
            else:
                sd=st.text_input("","",placeholder="Filter files…",key="fsd",label_visibility="collapsed")
                for f in docx_list:
                    if sd and sd.lower() not in f.stem.lower(): continue
                    mtime=datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%y %H:%M")
                    kb=f.stat().st_size//1024
                    nc,ic,bc=st.columns([4,2,1])
                    with nc: st.markdown(f'<div style="padding:.3rem 0;font-size:.84rem">📝 {f.stem[:55]}</div>',unsafe_allow_html=True)
                    with ic: st.markdown(f'<div style="padding:.35rem 0;font-size:.71rem;color:var(--t3)">{kb}KB · {mtime}</div>',unsafe_allow_html=True)
                    with bc: st.download_button("⬇",data=f.read_bytes(),file_name=f.name,
                                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 key=f"dl_{f.name}",use_container_width=True)
        with t2:
            if not txt_list: st.caption("No TXT files.")
            else:
                sel=st.selectbox("",[ f.name for f in txt_list],key="tp",label_visibility="collapsed")
                if sel:
                    fp=Path(out_dir)/sel
                    ct=fp.read_text(encoding="utf-8")
                    rc,dc=st.columns([4,1])
                    with rc: st.caption(f"{len(ct):,} characters")
                    with dc: st.download_button("⬇",ct.encode("utf-8"),file_name=sel,mime="text/plain",key="tdl")
                    st.code(ct[:2000],language=None)
    st.markdown('</div>',unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════
# LEARN
# ═════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="pg">',unsafe_allow_html=True)
    st.markdown('<div class="sec">🧠 Self-Improvement Engine</div>',unsafe_allow_html=True)
    st.markdown('<div class="info">Upload a corrected DOCX — system automatically finds every difference and learns from all of them at once. Every future transcription improves.</div>',unsafe_allow_html=True)
    st.markdown("")
    try:
        from learner import get_stats
        stats=get_stats(prog_file.replace("progress.json","corrections.json"))
        s1,s2,s3,s4=st.columns(4)
        s1.metric("📚 Learned",stats.get("total_pairs",0))
        s2.metric("📖 Episodes",stats.get("episodes_learned_from",0))
        s3.metric("✅ Applied",stats.get("total_corrections_applied",0))
        s4.metric("🕐 Updated",stats.get("last_updated","—")[:10] if stats.get("last_updated") else "—")
        if stats.get("top_corrections"):
            st.markdown('<div class="sec">Top Corrections</div>',unsafe_allow_html=True)
            rows=""
            for item in stats["top_corrections"][:8]:
                w=item.get("wrong","") or "(delete)"; c=item.get("correct","") or "(removed)"
                rows+=(f'<div class="cr"><span class="cw">{w}</span>'
                       f'<span style="color:var(--t3)">→</span>'
                       f'<span class="cc">{c}</span><span class="cn">×{item["count"]}</span></div>')
            st.markdown(rows,unsafe_allow_html=True)
    except: st.caption("No corrections yet.")
    st.markdown("")
    lc,rc=st.columns([3,2])
    with lc:
        st.markdown('<div class="sec">Upload Corrected File</div>',unsafe_allow_html=True)
        uploaded=st.file_uploader("Drop DOCX",type=["docx"],label_visibility="collapsed")
        txt_list_l=sorted(Path(out_dir).glob("*.txt"),key=lambda f:f.stat().st_mtime,reverse=True) if Path(out_dir).exists() else []
        if uploaded:
            stem=Path(uploaded.name).stem
            matched=next((t for t in txt_list_l if t.stem==stem),None)
            if matched: st.success(f"✓ Matched: {matched.name}")
            else:
                st.warning("Select original TXT:")
                sel2=st.selectbox("",[ f.name for f in txt_list_l],label_visibility="collapsed")
                matched=Path(out_dir)/sel2 if sel2 else None
            if matched and st.button("🧠 Learn from this file",use_container_width=True):
                import tempfile,os as _os
                with st.spinner("Analysing differences…"):
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".docx",delete=False) as tf:
                            tf.write(uploaded.read()); tmp=tf.name
                        from learner import learn_from_files
                        result=learn_from_files(str(matched),tmp,
                            corrections_path=prog_file.replace("progress.json","corrections.json"))
                        _os.unlink(tmp)
                        if "error" in result: st.error(result["error"])
                        else:
                            st.success(f"✅ {result['new_pairs']} new · {result['updated_pairs']} reinforced · {result['total_in_db']} total")
                            st.rerun()
                    except Exception as e: st.error(f"Failed: {e}")
    with rc:
        st.markdown("""<div class="info"><b>Steps:</b><br>
        1. Transcribe a video<br>2. Download DOCX from Files<br>
        3. Fix all errors in Word<br>4. Upload corrected file here<br>
        5. System learns everything<br>6. Next video is more accurate</div>""",unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════
# HELP
# ═════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="pg">',unsafe_allow_html=True)
    st.markdown('<div class="sec">How to Use</div>',unsafe_allow_html=True)
    for num,title,desc in [
        ("1","Transcribe a video","Transcribe tab → paste URL → Fetch → Start"),
        ("2","Watch live progress","Dashboard tab auto-refreshes with live log + percent"),
        ("3","Download & correct","Files tab → download DOCX → fix in Word"),
        ("4","Upload for learning","Learn tab → upload corrected DOCX → system improves"),
        ("5","Paste into InPage","Copy corrected text → paste into InPage → format & print"),
        ("6","Resume after stop","Run same command again — completed videos are always skipped"),
    ]:
        st.markdown(f'<div class="step"><div class="sn">{num}</div><div><div class="st">{title}</div><div class="sd">{desc}</div></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="sec">Fix 403 Download Error</div>',unsafe_allow_html=True)
    st.markdown("""<div class="info">If you see <b>HTTP Error 403: Forbidden</b> when downloading:<br><br>
    Run this in terminal: <code>pip install --upgrade yt-dlp</code><br><br>
    This updates yt-dlp to bypass YouTube restrictions. Do this whenever downloads fail.</div>""",unsafe_allow_html=True)
    st.markdown('<div class="sec">Important Settings</div>',unsafe_allow_html=True)
    st.markdown("""<div class="info">
    <b>Model:</b> Always use <code>medium</code> for best Urdu/Persian accuracy<br>
    <b>CPU Threads:</b> Keep at 4 — your i5-4570 has exactly 4 cores<br>
    <b>Mid-job change:</b> Safe — current video uses old model, next uses new<br>
    <b>Deploy online:</b> Push to GitHub → share.streamlit.io → select app.py → Deploy
    </div>""",unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)
