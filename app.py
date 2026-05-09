"""
Masnavi Transcription System — Cloud Collaborative App
=======================================================
Run locally : streamlit run app.py
Deploy free : https://share.streamlit.io  OR  https://railway.app

Features
--------
• Any team member opens the URL on phone / laptop / PC
• Shared live dashboard — who did what, what's remaining
• One-click transcription of any pending video
• DOCX file browser — download and correct transcripts
• Progress persists in JSON — resume after any restart
"""

import streamlit as st
import json, os, time, threading
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="مثنوی ٹرانسکرپشن",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
:root{--ink:#1a1409;--parchment:#f7f1e3;--gold:#b8860b;--gold-l:#d4a843;--rust:#8b2500;--border:#c8b87a;--muted:#6b5e3e}
html,body,[class*="css"]{font-family:'Crimson Pro',Georgia,serif}
#MainMenu,footer,header{visibility:hidden}
.main{background:var(--parchment)}
.block-container{padding:1.5rem 2rem 4rem;max-width:1300px}
h1{font-size:2.1rem;color:var(--ink);border-bottom:2px solid var(--gold);padding-bottom:.4rem}
h2{font-size:1.4rem;color:var(--ink)}
h3{font-size:1.1rem;color:var(--rust)}
[data-testid="metric-container"]{background:white;border:1px solid var(--border);border-radius:8px;padding:1rem 1.2rem;box-shadow:0 1px 3px rgba(0,0,0,.06)}
[data-testid="metric-container"] label{color:var(--muted)!important;font-size:.78rem!important;text-transform:uppercase;letter-spacing:.08em}
[data-testid="metric-container"] [data-testid="metric-value"]{color:var(--ink)!important;font-size:1.8rem!important;font-weight:600!important}
.stButton>button{background:var(--ink)!important;color:var(--parchment)!important;border:none!important;border-radius:6px!important;font-family:'Crimson Pro',serif!important;font-size:.95rem!important;padding:.45rem 1.4rem!important;transition:background .2s}
.stButton>button:hover{background:var(--rust)!important}
.stProgress>div>div{background:var(--gold)!important;border-radius:4px}
.stProgress>div{background:#e8dfc8!important;border-radius:4px}
.badge{display:inline-block;padding:2px 9px;border-radius:12px;font-size:.72rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.b-done{background:#d4edda;color:#155724}
.b-pend{background:#fff3cd;color:#856404}
.b-proc{background:#cce5ff;color:#004085}
.b-fail{background:#f8d7da;color:#721c24}
.video-row{display:flex;align-items:center;gap:10px;padding:.55rem .8rem;border-bottom:1px solid #ede4cc;font-size:.88rem}
.video-row:hover{background:#fdf8ef}
.vnum{color:var(--muted);min-width:28px;font-size:.78rem}
.vtitle{flex:1;font-family:'Noto Nastaliq Urdu',serif;direction:rtl;text-align:right;font-size:1rem}
.log-box{background:#1a1409;color:#c8b87a;font-family:'Courier New',monospace;font-size:.74rem;line-height:1.6;padding:.9rem;border-radius:6px;max-height:220px;overflow-y:auto;white-space:pre-wrap}
.info-box{background:#fffbf0;border-left:4px solid var(--gold);border-radius:0 6px 6px 0;padding:.75rem 1.1rem;margin:.6rem 0;font-size:.93rem;color:var(--ink)}
.ornament{text-align:center;color:var(--gold);font-size:1.2rem;margin:.3rem 0;letter-spacing:.3em}
[data-testid="stSidebar"]{background:var(--ink)!important;border-right:3px solid var(--gold)}
[data-testid="stSidebar"] *{color:var(--parchment)!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{border:none!important;color:var(--gold-l)!important}
[data-testid="stSidebar"] .stSelectbox>div>div{background:#2d2414!important;border-color:var(--gold)!important}
[data-testid="stSidebar"] .stTextInput>div>div>input{background:#2d2414!important;border-color:var(--gold)!important;color:var(--parchment)!important}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"videos":[],"logs":[],"processing":False,"cur_video":"","cur_stage":"","cur_pct":0.0,"playlist_url":""}.items():
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
    c = {"completed":"b-done","pending":"b-pend","processing":"b-proc","failed":"b-fail"}.get(status,"b-pend")
    l = {"completed":"✓ مکمل","pending":"⏳ باقی","processing":"⚙ جاری","failed":"✗ ناکام"}.get(status,status)
    return f'<span class="badge {c}">{l}</span>'

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📜 مثنوی ٹرانسکرپشن")
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    model_size  = st.selectbox("Whisper Model",["tiny","base","small","medium","large-v2"],index=3)
    cpu_threads = st.slider("CPU Threads", 1, 16, 4, help="Set to your machine's core count for max speed")
    language    = st.selectbox("Primary Language",["ur (Urdu)","fa (Persian)","ar (Arabic)"],index=0)
    lang_code   = language.split()[0]
    out_dir     = st.text_input("Transcripts folder", TRANSCRIPT_DIR)
    audio_dir   = st.text_input("Audio cache",        AUDIO_DIR)
    prog_file   = st.text_input("Progress file",      PROGRESS_FILE)
    st.markdown("---")
    st.markdown("### 📐 Speed vs Accuracy")
    for m,(sp,ac) in {"tiny":("⚡⚡⚡⚡","★☆☆☆"),"base":("⚡⚡⚡","★★☆☆"),"small":("⚡⚡","★★★☆"),"medium":("⚡","★★★★"),"large-v2":("🐢","★★★★★")}.items():
        st.markdown(f"`{m}` {sp} {ac}")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 📜 مثنوی لیکچر ٹرانسکرپشن سسٹم")
st.markdown('<div class="ornament">✦ ✦ ✦</div>', unsafe_allow_html=True)
st.caption("Masnavi Lecture Transcription System — Team Collaboration Dashboard")

tab_dash, tab_new, tab_files, tab_learn, tab_help = st.tabs(["📊 Team Dashboard","🎬 Transcribe","📂 Files","🧠 Learn","❓ Help"])


# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
with tab_dash:
    data = load_tracker(prog_file)

    if not data:
        st.markdown('<div class="info-box">No job started yet. Go to the <b>Transcribe</b> tab to load a playlist.</div>', unsafe_allow_html=True)
    else:
        vids  = data.get("videos", {})
        total = data.get("total", 0)
        done  = sum(1 for v in vids.values() if v["status"]=="completed")
        proc  = sum(1 for v in vids.values() if v["status"]=="processing")
        fail  = sum(1 for v in vids.values() if v["status"]=="failed")
        pend  = sum(1 for v in vids.values() if v["status"]=="pending")
        pct   = round(done/max(total,1)*100,1)

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📹 کل", total)
        c2.metric("✅ مکمل", done)
        c3.metric("⚙️ جاری", proc)
        c4.metric("⏳ باقی", pend)
        c5.metric("❌ ناکام", fail)
        c6.metric("📈 %", f"{pct}%")
        st.progress(pct/100)
        st.caption(f"Playlist: {data.get('playlist_url','—')[:80]}")
        st.markdown("")

        fc1,fc2 = st.columns([2,3])
        with fc1: flt    = st.selectbox("Filter",["all","pending","completed","processing","failed"])
        with fc2: search = st.text_input("Search title", placeholder="type to search…")

        st.markdown("### Video Status")
        shown = 0
        for i,(vid_id,info) in enumerate(vids.items(),1):
            if flt!="all" and info["status"]!=flt: continue
            title = info.get("title",vid_id)
            if search and search.lower() not in title.lower(): continue
            shown += 1
            b  = badge(info["status"])
            ts = datetime.fromtimestamp(info["completed_at"]).strftime("%m/%d %H:%M") if info.get("completed_at") else ""
            doc = f'<span style="font-size:.72rem;color:#1a5f5a">📄 {Path(info["transcript_path"]).stem[:30]}.docx</span>' if info.get("transcript_path") else ""
            st.markdown(
                f'<div class="video-row"><span class="vnum">#{i}</span>'
                f'<span style="flex:1;color:var(--ink)">{title[:65]}</span>'
                f'{b} <span style="font-size:.7rem;color:var(--muted);min-width:80px">{ts}</span>{doc}</div>',
                unsafe_allow_html=True)
        if shown==0: st.info("No videos match.")

    if st.session_state.logs:
        st.markdown("### 📋 Log")
        log_text = "\n".join(st.session_state.logs[-50:])
        st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

    if st.session_state.processing:
        st.markdown(f"**⚙ Processing:** {st.session_state.cur_video[:80]}")
        st.progress(st.session_state.cur_pct/100, text=f"{st.session_state.cur_stage} — {st.session_state.cur_pct:.1f}%")
        time.sleep(3); st.rerun()

    cr,_ = st.columns([1,5])
    with cr:
        if st.button("🔄 Refresh"): st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TRANSCRIBE
# ════════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.markdown("### یو ٹیوب لنک داخل کریں")
    job_type  = st.radio("Job type",["Full Playlist","Single Video"],horizontal=True)
    url_input = st.text_input("YouTube URL", placeholder="https://www.youtube.com/playlist?list=...")

    ca,cb,_ = st.columns([2,2,4])
    with ca:
        if st.button("🔍 Fetch Videos", use_container_width=True):
            if not url_input.strip():
                st.error("Enter a URL first.")
            else:
                with st.spinner("Fetching…"):
                    try:
                        if job_type=="Full Playlist":
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

    if st.session_state.videos:
        st.success(f"✓ {len(st.session_state.videos)} video(s) found")
        for i,v in enumerate(st.session_state.videos[:15],1):
            st.markdown(f'<div class="video-row"><span class="vnum">#{i}</span><span class="vtitle">{v["title"]}</span></div>', unsafe_allow_html=True)
        if len(st.session_state.videos)>15:
            st.caption(f"… and {len(st.session_state.videos)-15} more")

    with cb:
        if st.button("▶ Start Transcription", use_container_width=True,
                     disabled=not st.session_state.videos or st.session_state.processing):

            def run_job(videos, model, lang, threads, odir, adir, pfile):
                try:
                    from progress_tracker import ProgressTracker
                    from transcriber import download_audio, transcribe_audio, save_transcript
                    tracker = ProgressTracker(save_path=pfile)
                    tracker.init_playlist(st.session_state.playlist_url or videos[0]["url"], videos)
                    pending = tracker.pending_videos()
                    add_log(f"Job started — {len(pending)} queued")

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
                            tracker.mark_failed(vid_id,"Download failed"); add_log("  ✗ Download failed"); continue

                        audio_path,_ = res
                        add_log("  ✓ Downloaded")
                        transcript = transcribe_audio(audio_path, language=lang, model_size=model,
                                                      progress_cb=prog, device="cpu",
                                                      compute_type="int8", cpu_threads=threads)
                        if os.path.exists(audio_path): os.remove(audio_path)

                        if not transcript:
                            tracker.mark_failed(vid_id,"Transcription failed"); add_log("  ✗ Failed"); continue

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
            threading.Thread(target=run_job,
                args=(st.session_state.videos, model_size, lang_code,
                      cpu_threads, out_dir, audio_dir, prog_file), daemon=True).start()
            st.info("✓ Job started — watch the **Team Dashboard** tab.")


# ════════════════════════════════════════════════════════════════════════════════
# FILES
# ════════════════════════════════════════════════════════════════════════════════
with tab_files:
    st.markdown("### 📂 Transcript Files")
    st.markdown('<div class="info-box">Download DOCX → open in Word / WPS Office → correct errors → print. The TXT files are for the future chatbot database.</div>', unsafe_allow_html=True)

    docx_list = sorted(Path(out_dir).glob("*.docx"), key=lambda f:f.stat().st_mtime, reverse=True) if Path(out_dir).exists() else []
    txt_list  = sorted(Path(out_dir).glob("*.txt"),  key=lambda f:f.stat().st_mtime, reverse=True) if Path(out_dir).exists() else []

    if not docx_list and not txt_list:
        st.info(f"No files yet in `{out_dir}/`")
    else:
        d1,d2,d3 = st.columns(3)
        d1.metric("📝 DOCX", len(docx_list))
        d2.metric("📄 TXT",  len(txt_list))
        d3.metric("💾 Size MB", f"{sum(f.stat().st_size for f in docx_list+txt_list)/1_048_576:.1f}")
        st.markdown("")

        ft1,ft2 = st.tabs(["📝 DOCX — Edit & Print","📄 TXT — Database"])

        with ft1:
            if not docx_list:
                st.info("No DOCX files yet.")
            else:
                sd = st.text_input("Search", key="ds", placeholder="filter by name…")
                for f in docx_list:
                    if sd and sd.lower() not in f.stem.lower(): continue
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    n,i,b2 = st.columns([4,2,1])
                    with n: st.markdown(f"📝 **{f.stem[:55]}**")
                    with i: st.caption(f"{f.stat().st_size//1024} KB • {mtime}")
                    with b2:
                        st.download_button("⬇", data=f.read_bytes(), file_name=f.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{f.name}")

        with ft2:
            if not txt_list:
                st.info("No TXT files yet.")
            else:
                sel = st.selectbox("Select file to preview", [f.name for f in txt_list])
                if sel:
                    fp = Path(out_dir)/sel
                    content = fp.read_text(encoding="utf-8")
                    rc,dc = st.columns([4,1])
                    with rc: st.caption(f"{len(content):,} chars")
                    with dc:
                        st.download_button("⬇", content.encode("utf-8"), file_name=sel,
                                           mime="text/plain; charset=utf-8", key="txt_dl")
                    st.code(content[:2000], language=None)


# ════════════════════════════════════════════════════════════════════════════════
# HELP
# ════════════════════════════════════════════════════════════════════════════════
with tab_help:
    st.markdown("### How to use")
    st.markdown("""
**Step 1** — Go to **Transcribe** → paste playlist URL → Fetch → Start Transcription.

**Step 2** — Watch **Team Dashboard** — every video shows status in real time. 
Share this app URL with team members — everyone sees the same progress.

**Step 3** — Go to **Files** → download any DOCX → open in Word → fix errors → save & print.

**Step 4** — If system restarts, click Start again — completed videos are skipped automatically.
""")

    st.markdown("---")
    st.markdown("### Deploying online for your team")
    st.markdown("""
**Option A — Streamlit Community Cloud (Free)**
1. Upload your code to GitHub (private repo is fine)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → select `app.py` → Deploy
4. Share the URL with your team — done

**Option B — Railway.app (~$5/month, persistent storage)**
1. Push code to GitHub
2. New project on [railway.app](https://railway.app) → Deploy from GitHub
3. Add a persistent volume mounted at `/app/transcripts`
4. Team accesses via the Railway URL

**Option C — Local network (free, same WiFi)**
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
Anyone on the same WiFi opens: `http://YOUR_IP:8501`
""")

    st.markdown("---")
    st.markdown("### Accuracy improvement tips")
    st.markdown("""
- **medium model** = best balance for Urdu/Persian on CPU
- **large-v2** = highest accuracy, but 3x slower — good overnight batch
- **CPU Threads** = set to your machine's core count (4 cores → set 4)
- The system already injects an Urdu/Persian context prompt into Whisper to reduce English hallucinations
""")


# ════════════════════════════════════════════════════════════════════════════════
# LEARN TAB — Upload corrected DOCX, system learns automatically
# ════════════════════════════════════════════════════════════════════════════════
with tab_learn:
    st.markdown("### 🧠 Self-Improvement Engine")
    st.markdown("""
<div class="info-box">
<b>How it works:</b><br>
1. System transcribes a video → saves original TXT + DOCX<br>
2. You open the DOCX in Word, fix all mistakes, save it<br>
3. Upload the corrected DOCX here — system finds ALL differences automatically<br>
4. Every future transcription is automatically improved using what it learned<br>
<br>
<b>No need to list mistakes one by one.</b> Just upload the whole corrected file.
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Stats panel ──────────────────────────────────────────────────────
    try:
        from learner import get_stats
        stats = get_stats(prog_file.replace("progress.json","corrections.json"))
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("📚 Corrections Learned",  stats.get("total_pairs",0))
        s2.metric("📖 Episodes Fed Back",    stats.get("episodes_learned_from",0))
        s3.metric("✅ Total Auto-Applied",   stats.get("total_corrections_applied",0))
        s4.metric("🕐 Last Updated",
                  stats.get("last_updated","never")[:10] if stats.get("last_updated") else "never")

        if stats.get("top_corrections"):
            st.markdown("#### 🔝 Most Frequent Corrections Learned")
            for item in stats["top_corrections"][:8]:
                wrong   = item["wrong"]   or "(delete)"
                correct = item["correct"] or "(removed)"
                count   = item["count"]
                st.markdown(
                    f'<div class="video-row">'
                    f'<span style="color:#9b2335;font-family:\'Noto Nastaliq Urdu\',serif;direction:rtl;flex:1">{wrong}</span>'
                    f'<span style="color:#888;padding:0 12px">→</span>'
                    f'<span style="color:#2d6a4f;font-family:\'Noto Nastaliq Urdu\',serif;direction:rtl;flex:1">{correct}</span>'
                    f'<span style="color:var(--muted);font-size:.75rem;min-width:60px">×{count}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.info("No corrections learned yet. Upload your first corrected DOCX below.")

    st.markdown("---")
    st.markdown("### Upload Corrected DOCX")

    # ── File uploader ────────────────────────────────────────────────────
    col_up, col_info = st.columns([3, 2])

    with col_up:
        uploaded = st.file_uploader(
            "Upload corrected DOCX file",
            type=["docx"],
            help="Open the DOCX in Word, fix all mistakes, save, then upload here."
        )

        # Match with original TXT
        txt_list_l = sorted(Path(out_dir).glob("*.txt"),
                            key=lambda f: f.stat().st_mtime, reverse=True) \
                     if Path(out_dir).exists() else []

        if uploaded:
            # Try to auto-match by filename
            upload_stem = Path(uploaded.name).stem
            matched_txt = None
            for tf in txt_list_l:
                if tf.stem == upload_stem:
                    matched_txt = tf
                    break

            if matched_txt:
                st.success(f"✓ Matched with original: `{matched_txt.name}`")
            else:
                st.warning("Could not auto-match. Please select the original TXT manually.")
                sel_txt = st.selectbox("Select original TXT", [f.name for f in txt_list_l])
                matched_txt = Path(out_dir) / sel_txt if sel_txt else None

            if matched_txt and st.button("🧠 Learn from this correction", use_container_width=True):
                import tempfile, os as _os
                with st.spinner("Diffing original vs corrected — finding all differences…"):
                    try:
                        # Save uploaded DOCX to temp file
                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
                            tf.write(uploaded.read())
                            tmp_docx = tf.name

                        from learner import learn_from_files
                        corr_file = prog_file.replace("progress.json", "corrections.json")
                        result = learn_from_files(
                            str(matched_txt),
                            tmp_docx,
                            corrections_path=corr_file,
                        )
                        _os.unlink(tmp_docx)

                        if "error" in result:
                            st.error(f"Error: {result['error']}")
                        else:
                            st.success(
                                f"✅ Learning complete!\n\n"
                                f"• **{result['new_pairs']}** new corrections added\n"
                                f"• **{result['updated_pairs']}** existing corrections reinforced\n"
                                f"• **{result['total_in_db']}** total corrections in database\n\n"
                                f"All future transcriptions will be automatically improved."
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Learning failed: {e}")

    with col_info:
        st.markdown("""
<div class="info-box">
<b>Workflow:</b><br><br>
<b>Step 1</b> — After a video is transcribed, go to the <b>Files</b> tab and download the DOCX.<br><br>
<b>Step 2</b> — Open in Microsoft Word. Correct all mistakes. Save the file.<br><br>
<b>Step 3</b> — Upload the corrected DOCX here.<br><br>
<b>Step 4</b> — System compares automatically, learns all differences.<br><br>
<b>Step 5</b> — Next video is transcribed with all those corrections applied.<br><br>
The more episodes you feed back, the better it gets.
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="info-box">
<b>What it learns:</b><br>
• Roman/English words → correct Urdu script<br>
• Wrong speaker names → correct spelling<br>
• Misheard Islamic terms → correct Arabic form<br>
• Recurring pronunciation errors → fixed<br>
• Anything you consistently correct
</div>
""", unsafe_allow_html=True)
