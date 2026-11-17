from __future__ import annotations

from typing import Any

from jobradar.models import Job


def generate_drafts(job: Job, profile: dict[str, Any]) -> dict[str, str | list[str]]:
    achievements = profile.get("achievements", [])
    selected = job.match_explanation.get("candidate_strengths", []) or achievements[:4]
    bullets = [f"{item}." for item in selected]
    cover = (f"Dear Hiring Team,\n\nI am interested in the {job.title} opportunity at {job.company}. "
             "My background includes global operations, business process improvement, and coordination between business and technical teams. "
             f"Relevant experience includes: {'; '.join(selected[:3])}.\n\n"
             "I would welcome a conversation about the role and how my verified experience could support your team. "
             "I am based in Taiwan and would be glad to clarify the employment arrangement and time-zone expectations.\n\nSincerely,\nSummer Yin")
    questions = job.recruiter_questions or ["Can this position employ a Taiwan resident, and through which employing entity?", "Is Taiwan EOR employment available, or is a B2B contractor arrangement required?", "What regular meeting overlap is expected with Asia/Taipei (UTC+8)?"]
    prompt = f"""LLM PROMPT PACKAGE — REVIEW AND EDIT BEFORE USE

Job title: {job.title}
Company: {job.company}
Posting URL: {job.original_url}

JOB DESCRIPTION
{job.description}

VERIFIED CANDIDATE ACHIEVEMENTS (use only these; do not add claims)
{chr(10).join('- ' + item for item in selected)}

TASK
Draft a tailored resume summary and cover letter using only the verified achievements above. Do not invent titles, dates, budgets, results, tools, or qualifications. Identify any requirements not supported by this profile. Keep all output as an editable draft for Summer Yin's review."""
    return {"resume_bullet_recommendations": bullets, "selected_achievements": selected, "cover_letter_draft": cover, "interview_questions": [f"How would you approach {area}?" for area in ("aligning global stakeholders across process change", "measuring success for this role", "coordinating business and technical teams")], "recruiter_questions": questions, "skills_gaps": job.match_explanation.get("missing_qualifications", []), "llm_prompt_package": prompt}
