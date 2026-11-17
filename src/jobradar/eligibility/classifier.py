from __future__ import annotations

import re
from datetime import datetime, timezone

from jobradar.models import Job

EXCLUSION_PATTERNS = [
    r"\bUS(?:A)?[- ]only\b", r"\bUnited States only\b", r"\bCanada only\b", r"\bUK only\b", r"\bUnited Kingdom only\b",
    r"\bEU(?:rope)?[- ]only\b", r"\bEurope only\b", r"\bmust be located in (?:the )?(?:US|United States|Canada|UK|United Kingdom|EU|Europe)\b",
    r"\bnot (?:available|open) (?:in|to) Taiwan\b", r"\bexcluding Taiwan\b", r"\bTaiwan is (?:not|excluded)\b",
    r"\bsecurity clearance\b", r"\brelocation required\b", r"\brelocate to\b", r"\bmandatory (?:office|hybrid)\b",
]
TAIWAN = re.compile(r"\bTaiwan(?:ese)?\b|\bTW\b", re.I)
WORLDWIDE = re.compile(r"\bworldwide\b|\bwork from anywhere\b|\bglobal remote\b|\banywhere in the world\b", re.I)
CONTRACT_SIGNALS = re.compile(r"\b(?:Deel|Remote\.com|Oyster|Papaya Global|Employer of Record|EOR|Independent Contractor|B2B contract|contractor[- ]friendly)\b", re.I)
APAC = re.compile(r"\b(?:APAC|Asia[- ]Pacific|Asia|UTC\s*\+?8|GMT\s*\+?8)\b", re.I)
ONSITE = re.compile(r"\b(?:onsite|on-site|in[- ]office|hybrid)\b", re.I)
QUESTIONS = [
    "Can you hire a candidate who resides in Taiwan, and which employing entity would be used?",
    "Is the role available through a Taiwan EOR, or as a compliant independent contractor/B2B engagement?",
    "Are there country-specific payroll, work authorization, or time-zone requirements for this role?",
]


def classify(job: Job) -> Job:
    text = f"{job.title}\n{job.location}\n{job.description}"
    reasons: list[str] = []
    evidence: list[str] = []
    status = "UNCERTAIN"
    for pattern in EXCLUSION_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            evidence.append(match.group(0))
            reasons.append("Posting contains an explicit geographic, clearance, relocation, or attendance restriction.")
            status = "INELIGIBLE"
            break
    if status != "INELIGIBLE":
        if ONSITE.search(text) and not re.search(r"remote|work from home", text, re.I):
            status = "INELIGIBLE"
            evidence.append(ONSITE.search(text).group(0))
            reasons.append("Posting indicates on-site or hybrid work without a remote option.")
        elif TAIWAN.search(text):
            status = "CONFIRMED"
            match = TAIWAN.search(text)
            evidence.append(text[max(0, match.start()-90):min(len(text), match.end()+100)].strip())
            reasons.append("The posting explicitly names Taiwan.")
        elif WORLDWIDE.search(text):
            status = "CONFIRMED"
            match = WORLDWIDE.search(text)
            evidence.append(text[max(0, match.start()-60):min(len(text), match.end()+100)].strip())
            reasons.append("The posting explicitly offers worldwide work and has no Taiwan exclusion found.")
        elif CONTRACT_SIGNALS.search(text) and (WORLDWIDE.search(text) or TAIWAN.search(text)):
            status = "CONFIRMED"
            match = CONTRACT_SIGNALS.search(text)
            evidence.append(text[max(0, match.start()-70):min(len(text), match.end()+100)].strip())
            reasons.append("A global contractor/EOR signal appears alongside explicit Taiwan or worldwide availability.")
        elif APAC.search(text):
            status = "UNCERTAIN"
            match = APAC.search(text)
            evidence.append(text[max(0, match.start()-60):min(len(text), match.end()+90)].strip())
            reasons.append("APAC or Asia timezone is mentioned, but hiring-country eligibility is not confirmed.")
        else:
            reasons.append("No reliable evidence confirms that a Taiwan-based candidate can be engaged.")
    job.eligibility_status = status
    job.eligibility_evidence = evidence
    job.eligibility_reasoning = " ".join(reasons)
    job.recruiter_questions = [] if status == "CONFIRMED" else QUESTIONS.copy()
    job.last_verified = datetime.now(timezone.utc)
    return job
