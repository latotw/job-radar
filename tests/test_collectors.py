import httpx

from jobradar.collectors.adapters import Collector


def test_remoteok_json_adapter_normalizes_public_job():
    body = [{"id": "42", "url": "https://remoteok.com/remote-jobs/42", "position": "Program Manager", "company": "Example", "description": "Worldwide remote", "tags": ["full-time"]}]
    collector = Collector(timeout=1, retries=0)
    collector.client.close()
    collector.client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    try:
        jobs = collector.remoteok()
    finally:
        collector.close()
    assert len(jobs) == 1
    assert jobs[0].source == "Remote OK"
    assert jobs[0].application_url == jobs[0].original_url


def test_rss_adapter_uses_original_link_and_summary():
    content = b"""<?xml version='1.0'?><rss version='2.0'><channel><item><title>Ops Manager</title><link>https://jobs.example/ops</link><description>Worldwide remote role</description><guid>ops-1</guid></item></channel></rss>"""
    collector = Collector(timeout=1, retries=0)
    collector.client.close()
    collector.client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content)))
    try:
        jobs = collector.rss("https://feed.example/jobs.rss", "Fixture RSS")
    finally:
        collector.close()
    assert jobs[0].original_url == "https://jobs.example/ops"
    assert "Worldwide" in jobs[0].description


def test_timestamp_dates_and_numeric_remoteok_salaries_are_supported():
    from datetime import datetime, timezone

    assert Collector._date(1_700_000_000_000) == datetime.fromtimestamp(1_700_000_000, timezone.utc)
    assert Collector._text(120000) == "120000"
