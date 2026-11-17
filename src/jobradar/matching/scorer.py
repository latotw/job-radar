from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from jobradar.config import load_yaml, profile
from jobradar.models import Job


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#]+", value.lower()))


def _fraction(haystack: set[str], terms: set[str]) -> float:
    return min(1.0, len(haystack & terms) / max(1, min(len(terms), 8)))


def score(job: Job, profile_data: dict[str, Any] | None = None, scoring: dict[str, Any] | None = None) -> Job:
    candidate = profile_data or profile()
    settings = scoring or load_yaml("scoring.yaml")
    weights = settings["weights"]
    text = f"{job.title} {job.description} {job.location}"
    words = _words(text)
    roles = candidate.get("target_roles", {})
    role_terms = _words(" ".join(roles.get("tier1", []) + roles.get("tier2", [])))
    achievements = candidate.get("achievements", [])
    skill_terms = _words(" ".join(achievements))
    industries = candidate.get("industries", [])
    industry_terms = _words(" ".join(industries))
    categories: dict[str, float] = {}
    categories["role_alignment"] = _fraction(words, role_terms)
    categories["skills_experience"] = _fraction(words, skill_terms)
    categories["industry_relevance"] = _fraction(words, industry_terms)
    categories["seniority"] = 0.7 if re.search(r"senior|lead|principal|manager|director|7\+", text, re.I) else 0.35
    target = settings.get("annual_compensation_target_twd", 2_000_000)
    annual_period = job.compensation_period.lower() in {"annual", "year", "yearly", "per year", "annually"}
    categories["compensation"] = 0.5 if not job.salary_text else (
        1.0 if annual_period and job.currency.upper() == "TWD" and job.salary_min is not None and job.salary_min >= target
        else 0.65 if annual_period and job.currency.upper() == "TWD" and job.salary_min is not None
        else 0.5
    )
    categories["timezone"] = 1.0 if re.search(r"async|APAC|Asia|UTC\s*\+?8|GMT\s*\+?8|Taiwan", text, re.I) else (0.55 if re.search(r"remote|worldwide", text, re.I) else 0.2)
    age_days = max(0, (datetime.now(timezone.utc) - job.published_at).days) if job.published_at else 15
    categories["freshness"] = max(0.0, 1 - age_days / max(1, settings.get("freshness_days", 30)))
    raw_score = sum(weights[key] * categories[key] for key in weights)
    job.fit_score = round(raw_score)
    matching = [a for a in achievements if _words(a) & words]
    job.match_explanation = {
        "category_scores": {key: round(value * weights[key], 1) for key, value in categories.items()},
        "why_it_matches": matching[:5],
        "candidate_strengths": matching[:5],
        "missing_qualifications": [],
        "potential_concerns": ["Taiwan employment eligibility needs confirmation."] if job.eligibility_status == "UNCERTAIN" else [],
        "recommended_resume_keywords": sorted((_words(job.title) & skill_terms) | (_words(job.description) & skill_terms))[:20],
    }
    return job


def detect_risks(job: Job) -> list[str]:
    text = f"{job.title}\n{job.company}\n{job.description}"
    risks: list[str] = []
    checks = [
        (r"upfront (?:payment|fee)|training fee|pay to apply|purchase equipment from", "Posting requests an upfront payment or training fee."),
        (r"bank details|crypto wallet|seed phrase|passport|identity document|social security number", "Posting requests sensitive financial or identity information; verify the hiring stage and employer first."),
        (r"\$\s?\d{3,}\s*(?:per hour|/hour).*(?:no experience|entry level)", "Salary claim may be unusually high for the described experience; verify independently."),
        (r"@(?:gmail|yahoo|hotmail|outlook)\.com", "Free webmail contact claims to represent an employer; verify the recruiter and domain."),
    ]
    for pattern, warning in checks:
        if re.search(pattern, text, re.I):
            risks.append(warning)
    if job.company.lower() in job.title.lower() and len(job.description.strip()) < 80:
        risks.append("Description is very short and may not substantiate the advertised position; verify the employer posting.")
    return risks
