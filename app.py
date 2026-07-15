"""
Post-Incident Report Generator — web interface.

Run with:
    streamlit run app.py
"""

import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from generator import get_client, generate_report, find_gaps
from exporters import to_docx, to_pdf

st.set_page_config(
    page_title="Post-Incident Report Generator",
    page_icon="📋",
    layout="wide",
)

# ---------------------------------------------------------------- header

st.title("Post-Incident Report Generator")
st.caption(
    "Turns a crisis call transcript — or raw incident notes — into a structured "
    "post-incident report, and tells you what the source is missing before you send it."
)

# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.header("Source")

    source_type = st.radio(
        "What are you working from?",
        ["Raw notes", "Call transcript"],
        help=(
            "Not every incident call can be recorded — client consent, internal "
            "incidents, smaller organisations. Both inputs are supported."
        ),
    )

    input_method = st.radio("How do you want to provide it?", ["Paste text", "Upload file"])

    st.divider()
    st.caption(
        "The report is written to be sent. The gap analysis is written for you — "
        "it flags what the source doesn't say, so nothing gets quietly filled in."
    )

# ---------------------------------------------------------------- input

source_text = ""

if input_method == "Paste text":
    source_text = st.text_area(
        "Paste the transcript or notes",
        height=280,
        placeholder="INC0049182 - payment gateway timeouts - P1\nfirst alert 14:02...",
    )
else:
    uploaded = st.file_uploader("Upload a .txt file", type=["txt", "md"])
    if uploaded:
        source_text = uploaded.read().decode("utf-8")
        with st.expander("Preview source"):
            st.text(source_text[:3000])

generate = st.button("Generate report", type="primary", disabled=not source_text.strip())

# ---------------------------------------------------------------- generate

if generate:
    kind = "transcript" if source_type == "Call transcript" else "notes"

    try:
        client = get_client()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    # Both calls are independent, so run them at the same time rather than
    # waiting for one to finish before starting the other.
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
                gaps = f"Gap analysis failed: {e}"

    st.session_state["report"] = report
    st.session_state["gaps"] = gaps

# ---------------------------------------------------------------- output

if "report" in st.session_state:
    report = st.session_state["report"]
    gaps = st.session_state["gaps"]

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Report")
        st.markdown(report)

    with right:
        st.subheader("What the source doesn't tell us")
        st.info(
            "This stays with you — it is not part of the report. "
            "Check these before sending."
        )
        st.markdown(gaps)

    st.divider()

    # Try to name the file after the incident ID, if the report contains one
    match = re.search(r"\b(INC\d+)\b", report)
    stem = match.group(1) if match else datetime.now().strftime("incident_%Y%m%d_%H%M")

    st.subheader("Download")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button(
            "Download DOCX",
            data=to_docx(report),
            file_name=f"{stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    with c2:
        st.download_button(
            "Download PDF",
            data=to_pdf(report),
            file_name=f"{stem}.pdf",
            mime="application/pdf",
        )

    with c3:
        st.download_button(
            "Download Markdown",
            data=report.encode("utf-8"),
            file_name=f"{stem}.md",
            mime="text/markdown",
        )
