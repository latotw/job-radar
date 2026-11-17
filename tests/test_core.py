from datetime import datetime, timezone

from jobradar.eligibility.classifier import classify
from jobradar.matching.scorer import detect_risks, score
from jobradar.models import Job
from jobradar.storage.database import JobStore


def job(description: str, **kwargs) -> Job:
    return Job(title="Business Operations Manager", company="Example", description=description, source="fixture", original_url="https://example.com/jobs/1", application_url="https://example.com/jobs/1", **kwargs)


def test_remote_label_alone_is_uncertain():
    result = classify(job("Remote role for experienced program manager."))
    assert result.eligibility_status == "UNCERTAIN"
    assert result.recruiter_questions


def test_worldwide_is_confirmed_and_evidence_saved():
    result = classify(job("This is a worldwide remote position."))
    assert result.eligibility_status == "CONFIRMED"
    assert result.eligibility_evidence
    assert result.last_verified


def test_country_restriction_wins_over_worldwide():
    result = classify(job("Worldwide remote, US-only payroll."))
    assert result.eligibility_status == "INELIGIBLE"


def test_apac_without_country_list_is_uncertain():
    assert classify(job("Remote within APAC.")).eligibility_status == "UNCERTAIN"


def test_taiwan_explicit_is_confirmed():
    assert classify(job("Candidates based in Taiwan may apply.")).eligibility_status == "CONFIRMED"


def test_score_is_deterministic_and_bounded():
    candidate = {"target_roles": {"tier1": ["Business Operations Manager"], "tier2": []}, "achievements": ["global operations"], "industries": ["Cybersecurity"]}
    item = job("Business Operations Manager for global operations in cybersecurity", published_at=datetime.now(timezone.utc))
    assert score(item, candidate, {"weights": {"role_alignment": 30, "skills_experience": 25, "industry_relevance": 10, "seniority": 10, "compensation": 10, "timezone": 10, "freshness": 5}}).fit_score > 50
    assert 0 <= item.fit_score <= 100


def test_risk_warnings_are_signals():
    item = job("Pay an upfront training fee and send your passport before interview.")
    warnings = detect_risks(item)
    assert len(warnings) >= 2


def test_store_deduplicates_and_preserves_pipeline(tmp_path):
    store = JobStore(tmp_path / "test.db")
    first = job("Worldwide remote")
    first.id = "fixture:1"
    assert store.upsert(first) == "new"
    store.update_pipeline(first.id, "Applied", "Applied manually")
    duplicate = first.model_copy(update={"title": "Business Operations Manager II", "description": "Updated worldwide remote"})
    assert store.upsert(duplicate) == "updated"
    saved = store.list_jobs()[0]
    assert saved.pipeline_status == "Applied"
    assert saved.personal_notes == "Applied manually"
