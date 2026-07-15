"""
Hindsight — incident report generator (web interface).

Run with:
    python -m streamlit run app.py
"""

import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from generator import get_client, generate_report, find_gaps
from exporters import to_docx, to_pdf

st.set_page_config(
    page_title="Hindsight — Incident Reports",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- styling
# Palette:
#   ink      #14181F  deep near-black navy (the incident, the night shift)
#   slate    #2B3440  secondary surfaces
#   mist     #F5F6F8  clean report surface (clarity)
#   amber    #E0A340  the accent: the moment it makes sense in hindsight
#   line     #E2E5EA  hairlines

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

    :root {
        --ink: #14181F;
        --slate: #2B3440;
        --mist: #F5F6F8;
        --amber: #E0A340;
        --line: #E2E5EA;
        --muted: #6B7280;
    }

    /* base type */
    html, body, [class*="css"], .stMarkdown, p, span, div, label {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* hide default streamlit chrome */
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }

    /* ---- brand header ---- */
    .hs-brand {
        display: flex; align-items: baseline; gap: 0.65rem;
        border-bottom: 1px solid var(--line);
        padding-bottom: 1.1rem; margin-bottom: 0.4rem;
    }
    .hs-mark {
        font-size: 1.5rem; color: var(--amber); line-height: 1;
        transform: translateY(2px);
    }
    .hs-name {
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 600; font-size: 1.9rem; letter-spacing: -0.01em;
        color: var(--ink);
    }
    .hs-tag {
        font-size: 0.9rem; color: var(--muted); margin-left: auto;
        align-self: center; font-weight: 500;
    }
    .hs-lede {
        color: var(--slate); font-size: 1.02rem; line-height: 1.55;
        margin: 0.9rem 0 0.4rem; max-width: 46rem;
    }
    .hs-lede b { color: var(--ink); font-weight: 600; }

    /* ---- section eyebrows ---- */
    .hs-eyebrow {
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.09em;
        text-transform: uppercase; color: var(--amber);
        margin: 0 0 0.5rem;
    }
    .hs-panel-title {
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 600; font-size: 1.15rem; color: var(--ink);
        margin: 0 0 0.15rem;
    }

    /* ---- buttons ---- */
    .stButton > button, .stDownloadButton > button {
        border-radius: 7px; font-weight: 600; font-family: 'Inter', sans-serif;
        border: 1px solid var(--line);
    }
    .stButton > button[kind="primary"] {
        background: var(--ink); border: 1px solid var(--ink); color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--slate); border-color: var(--slate);
    }

    /* ---- report surface ---- */
    .hs-report {
        background: #fff; border: 1px solid var(--line);
        border-radius: 10px; padding: 1.6rem 1.8rem;
    }
    .hs-report h2 {
        font-family: 'Fraunces', serif; font-size: 1.15rem;
        color: var(--ink); margin-top: 1.3rem; padding-top: 1.1rem;
        border-top: 1px solid var(--line);
    }
    .hs-report h2:first-child { border-top: none; padding-top: 0; margin-top: 0; }
    .hs-report table { font-size: 0.9rem; }

    /* ---- gap panel ---- */
    .hs-gaps {
        background: #FBF7EF; border: 1px solid #EAD9B8;
        border-left: 3px solid var(--amber);
        border-radius: 8px; padding: 1.1rem 1.3rem; font-size: 0.92rem;
    }

    /* sidebar */
    section[data-testid="stSidebar"] { background: var(--mist); border-right: 1px solid var(--line); }
    section[data-testid="stSidebar"] .hs-side-title {
        font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.05rem;
        color: var(--ink); margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- header

st.markdown("""
<div class="hs-brand">
    <span class="hs-mark">◐</span>
    <span class="hs-name">Hindsight</span>
    <span class="hs-tag">Post-incident reports, without the hour of writing</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p class="hs-lede">
Turn a crisis call transcript — or the notes you typed while everything was on fire —
into a clean post-incident report your client can read. <b>And before you send it,
Hindsight tells you what the source never actually said</b>, so nothing gets quietly
filled in.
</p>
""", unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown('<div class="hs-side-title">Source material</div>', unsafe_allow_html=True)
    st.caption("What are you turning into a report?")

    source_type = st.radio(
        "Type",
        ["Raw notes", "Call transcript"],
        label_visibility="collapsed",
        help=(
            "Not every incident call can be recorded — client consent, internal "
            "incidents, smaller shops. Both work here."
        ),
    )

    input_method = st.radio(
        "Input", ["Paste text", "Upload file"], label_visibility="collapsed"
    )

    st.divider()
    st.markdown(
        '<div style="font-size:0.8rem;color:#6B7280;line-height:1.5;">'
        'The <b>report</b> is written to be sent to a client.<br>'
        'The <b>gap check</b> is written for you — it flags what the source '
        "doesn't say, so you catch it before the client does.</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- input

source_text = ""

if input_method == "Paste text":
    source_text = st.text_area(
        "Paste the transcript or notes",
        height=260,
        placeholder="INC0049182 — payment gateway timeouts — P1\nfirst alert 14:02, checkout returning 504s...\nbridge opened 14:11...",
    )
else:
    uploaded = st.file_uploader("Upload a .txt file", type=["txt", "md"])
    if uploaded:
        source_text = uploaded.read().decode("utf-8")
        with st.expander("Preview source"):
            st.text(source_text[:3000])

generate = st.button(
    "Generate report", type="primary", disabled=not source_text.strip()
)

# ---------------------------------------------------------------- generate

if generate:
    kind = "transcript" if source_type == "Call transcript" else "notes"

    try:
        client = get_client()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    with st.spinner("Writing the report and checking the source..."):
        with ThreadPoolExecutor(max_workers=2) as pool:
            report_future = pool.submit(generate_report, client, source_text, kind)
            gaps_future = pool.submit(find_gaps, client, source_text, kind)

            try:
                report = report_future.result()
            except Exception as e:
                st.error(f"Report generation failed: {e}")
                st.stop()

            try:
                gaps = gaps_future.result()
            except Exception as e:
                gaps = f"Gap check failed: {e}"

    st.session_state["report"] = report
    st.session_state["gaps"] = gaps

# ---------------------------------------------------------------- output

if "report" in st.session_state:
    report = st.session_state["report"]
    gaps = st.session_state["gaps"]

    st.write("")
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown('<div class="hs-eyebrow">The report</div>', unsafe_allow_html=True)
        st.markdown('<div class="hs-panel-title">Ready to send</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown(report)

    with right:
        st.markdown('<div class="hs-eyebrow">Before you send</div>', unsafe_allow_html=True)
        st.markdown('<div class="hs-panel-title">What the source doesn\'t say</div>',
                    unsafe_allow_html=True)
        st.write("")
        st.markdown(f'<div class="hs-gaps">{gaps}</div>', unsafe_allow_html=True)

    st.write("")
    st.divider()

    match = re.search(r"\b(INC\d+)\b", report)
    stem = match.group(1) if match else datetime.now().strftime("incident_%Y%m%d_%H%M")

    st.markdown('<div class="hs-eyebrow">Download</div>', unsafe_allow_html=True)
    c1, c2, c3, _ = st.columns([1, 1, 1, 2])

    with c1:
        st.download_button(
            "Word (.docx)", data=to_docx(report), file_name=f"{stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "PDF", data=to_pdf(report), file_name=f"{stem}.pdf",
            mime="application/pdf", use_container_width=True,
        )
    with c3:
        st.download_button(
            "Markdown", data=report.encode("utf-8"), file_name=f"{stem}.md",
            mime="text/markdown", use_container_width=True,
        )
