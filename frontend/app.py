from __future__ import annotations
import io
import os
import textwrap
from pathlib import Path
from typing import List, Optional

import requests
import streamlit as st
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

BACKEND_URL: str = os.getenv("BACKEND_URL", "https://turtil-project.onrender.com").rstrip("/")
st.set_page_config(
    page_title="Turtil Resume ↔︎ Role Fit Evaluator",
    page_icon="🐢",
    layout="centered",
)

st.title("🐢 Turtil – Resume ⇆ Role Fit Evaluator")
st.write(
    "Paste your *resume* and the *job description* below, then click *Evaluate* "
    "to get the fit score, missing skills, and a personalised learning path."
)
def _read_pdf_pymupdf(data: bytes) -> Optional[str]:
    try:
        import fitz  # PyMuPDF
        text = ""
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for page in pdf:
                text += page.get_text("text")
        return text
    except Exception:
        return None

def _read_pdf_pypdf2(data: bytes) -> Optional[str]:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None

def _read_pdf_pdfminer(data: bytes) -> Optional[str]:
    try:
        from pdfminer.high_level import extract_text
        with io.BytesIO(data) as fp:
            return extract_text(fp)
    except Exception:
        return None

def _read_docx(data: bytes) -> Optional[str]:
    try:
        from docx import Document  # python-docx
        doc = Document(io.BytesIO(data))
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception:
        return None

def extract_text_safe(uploaded_file) -> str:
    """Try every parser; return '' if all fail."""
    data = uploaded_file.read()
    name = uploaded_file.name.lower()

    text: Optional[str] = None
    if name.endswith(".pdf"):
        for reader in (_read_pdf_pymupdf, _read_pdf_pypdf2, _read_pdf_pdfminer):
            text = reader(data)
            if text:
                break
    elif name.endswith(".docx"):
        text = _read_docx(data)

    if not text:
        st.warning(
            f"⚠️ Could not read *{uploaded_file.name}* – the file might be malformed "
            "or not a real PDF/DOCX. Please paste the text manually or upload a clean file."
        )
        text = ""
    uploaded_file.seek(0)
    return text.strip()

with st.sidebar:
    st.header("⚙️ Backend")
    st.write(f"Endpoint: {BACKEND_URL}")

    if st.button("🔎 Ping backend"):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=5)
            r.raise_for_status()
            st.success("Backend is up ✅")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Backend not reachable – {exc}")

    st.markdown(f"[Open API docs]({BACKEND_URL}/docs)")
with st.form("fit_form", clear_on_submit=False, border=True):
    st.subheader("1. Resume")
    resume_tab1, resume_tab2 = st.tabs(["📄 Paste text", "📑 Upload PDF / DOCX"])
    resume_text: str = ""

    with resume_tab1:
        resume_text = st.text_area(
            "Paste the *entire resume text* here ⬇️",
            height=250,
            placeholder="e.g. Experienced Python developer with 5 years…",
            key="resume_text_box",
        )

    with resume_tab2:
        resume_file = st.file_uploader(
            "Upload your resume (PDF or DOCX)",
            type=["pdf", "docx"],
            key="resume_file",
        )
        if resume_file is not None:
            resume_text = extract_text_safe(resume_file)
            if resume_text:
                st.success("Text extracted ✅ – you can edit it in the other tab.")
                resume_tab1.text_area(
                    "", resume_text, height=250, key="resume_text_extracted"
                )
    st.subheader("2. Job Description")
    jd_text = st.text_area(
        "Paste the *job description* here ⬇️",
        height=200,
        placeholder="e.g. We are looking for a Python backend engineer…",
        key="jd_text",
    )

    submitted = st.form_submit_button("🚀 Evaluate 📊")
if submitted:
    if not resume_text.strip() or not jd_text.strip():
        st.warning("Please provide *both* resume and job-description text.")
        st.stop()

    with st.spinner("Contacting backend, please wait…"):
        try:
            r = requests.post(
                f"{BACKEND_URL}/evaluate",
                json={"resume_text": resume_text, "job_description": jd_text},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.JSONDecodeError:
            st.error(
                "Received *non-JSON* response from backend – "
                "check that the FastAPI endpoint returns a proper dict."
            )
            st.stop()
        except Exception as exc:  # noqa: BLE001
            st.error(f"❌ Backend request failed – {exc}")
            st.stop()

    st.success("Analysis complete!")

    fit_score = data.get("fit_score")
    if fit_score is not None:
        st.metric("🟢 Fit Score", f"{fit_score * 100:.1f}%")

    missing_skills: List[str] = data.get("missing_skills", [])
    if missing_skills:
        st.subheader("🔍 Missing / Weak Skills")
        st.write(", ".join(f"*{s}*" for s in missing_skills) or "None – great match!")

    learning_path = data.get("recommended_learning_path", [])
    if learning_path:
        st.subheader("📚 Recommended Learning Path")
        for idx, step in enumerate(learning_path, 1):
            st.markdown(f"*{idx}. {step['skill']}*")
            for sub in step["steps"]:
                st.write("•", textwrap.fill(sub, 90))

    with st.expander("🛠 Raw backend response"):
        st.json(data)

st.divider()
st.caption("Made with ❤️ and 🐢 by Team Apogee · Backend: FastAPI · Front-end: Streamlit")
