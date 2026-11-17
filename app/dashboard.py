from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jobradar.application_assistant.drafts import generate_drafts
from jobradar.config import profile
from jobradar.storage.database import PIPELINE, JobStore

st.set_page_config(page_title="Global Remote Job Radar", layout="wide")
st.title("Global Remote Job Radar")
st.caption("Taiwan-aware discovery. Eligibility is evidence-based; applications and messages remain under your control.")
store = JobStore()
jobs = store.list_jobs()
tabs = st.tabs(["Top Matches", "Needs Verification", "Job Database", "Application Tracker", "Market Insights", "Weekly Review"])

with tabs[0]:
    for job in sorted([j for j in jobs if j.eligibility_status == "CONFIRMED"], key=lambda j: j.fit_score, reverse=True)[:30]:
        with st.expander(f"{job.fit_score}/100 · {job.company} — {job.title}"):
            st.write(job.match_explanation)
            st.caption(f"{job.source} · {job.employment_type} · {job.salary_text or 'Salary not disclosed'}")
            st.link_button("Open application", job.application_url)
with tabs[1]:
    for job in [j for j in jobs if j.eligibility_status == "UNCERTAIN"]:
        st.subheader(f"{job.company} — {job.title}")
        st.write(job.eligibility_reasoning, job.eligibility_evidence)
        st.write("Recruiter questions:", job.recruiter_questions)
        st.link_button("Open posting", job.application_url)
with tabs[2]:
    query = st.text_input("Search company, title, or description")
    status = st.multiselect("Eligibility", ["CONFIRMED", "UNCERTAIN", "INELIGIBLE"], default=["CONFIRMED", "UNCERTAIN", "INELIGIBLE"])
    filtered = [j for j in jobs if j.eligibility_status in status and query.lower() in f"{j.company} {j.title} {j.description}".lower()]
    st.dataframe(pd.DataFrame([{"Company": j.company, "Title": j.title, "Eligibility": j.eligibility_status, "Score": j.fit_score, "Type": j.employment_type, "Source": j.source, "Apply": j.application_url} for j in filtered]), width="stretch", hide_index=True)
with tabs[3]:
    if jobs:
        selected = st.selectbox("Choose a job", jobs, format_func=lambda j: f"{j.company} — {j.title}")
        new_status = st.selectbox("Pipeline status", PIPELINE, index=PIPELINE.index(selected.pipeline_status))
        notes = st.text_area("Personal notes", value=selected.personal_notes)
        if st.button("Save tracking update"):
            store.update_pipeline(selected.id, new_status, notes)
            st.success("Saved")
        if st.button("Generate application drafts"):
            st.session_state["drafts"] = generate_drafts(selected, profile())
        if "drafts" in st.session_state:
            for key, value in st.session_state["drafts"].items():
                st.subheader(key.replace("_", " ").title())
                st.text_area(key, value if isinstance(value, str) else "\n".join(value), height=220)
    else:
        st.info("Run a search to populate the tracker.")
with tabs[4]:
    if jobs:
        st.subheader("Eligibility distribution")
        st.bar_chart(pd.Series([j.eligibility_status for j in jobs]).value_counts())
        st.subheader("Employment types")
        st.bar_chart(pd.Series([j.employment_type for j in jobs]).value_counts().head(15))
        st.subheader("Sources")
        st.bar_chart(pd.Series([j.source for j in jobs]).value_counts())
    else:
        st.info("No stored opportunities yet.")
with tabs[5]:
    st.metric("Active jobs", len(jobs))
    st.metric("Confirmed Taiwan eligibility", sum(j.eligibility_status == "CONFIRMED" for j in jobs))
    st.metric("Shortlisted", sum(j.pipeline_status == "Shortlisted" for j in jobs))
