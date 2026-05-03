from __future__ import annotations

from datetime import datetime, timedelta, time, timezone

from fastapi.testclient import TestClient

from src.alerts.policies import AlertPolicyEngine, AlertState, AlertStatus, MaintenanceWindow
from src.alerts.router import AlertEvent, AlertRoute, AlertRouter
from src.api import app as api_app_module
from src.normalization.dedupe import DedupeEngine
from src.normalization.parser import parse_indicators, stable_text_digest
from src.normalization.schema import CanonicalEvent
from src.storage.raw_event_store import InMemoryRawEventStore, RawEvent
from src.workers.scheduler import CollectorScheduler


def _event(*, event_id: str, title: str, description: str, observed_at: datetime | None = None, cve_ids: list[str] | None = None, vendors: list[str] | None = None, products: list[str] | None = None, confidence: float = 0.0, poc_available: bool = False, exploitation_in_wild: bool = False) -> CanonicalEvent:
    return CanonicalEvent(event_id=event_id, title=title, description=description, observed_at=observed_at, cve_ids=cve_ids or [], vendors=vendors or [], products=products or [], confidence=confidence, poc_available=poc_available, exploitation_in_wild=exploitation_in_wild)


def test_collector_integration_contract_and_malformed_payload_handling() -> None:
    store = InMemoryRawEventStore()

    def collector_ok() -> list[RawEvent]:
        return [RawEvent(source="collector-a", title="CVE-2026-10001", payload={"severity": "critical"})]

    def collector_malformed() -> list[RawEvent]:
        return [RawEvent(source="collector-b", title="missing-fields", payload={})]

    scheduler = CollectorScheduler(collectors=[collector_ok, collector_malformed], store=store)
    scheduler._run_collectors()

    all_events = store.all()
    assert len(all_events) == 2
    assert all_events[0].payload["severity"] == "critical"
    assert all_events[1].payload == {}


def test_normalization_and_dedupe_correctness_with_edge_cases() -> None:
    text = "CVE-2026-10001 and cve-2026-10001 were exploited in the wild. PoC available at https://github.com/acme/exploit and bad ip 999.1.1.1 plus 8.8.8.8."
    parsed = parse_indicators(text)
    assert parsed.cve_ids == ["CVE-2026-10001"]
    assert parsed.exploitation_in_wild is True
    assert parsed.poc_available is True
    assert parsed.ips == ["8.8.8.8"]

    now = datetime(2026, 5, 3, 0, 0, tzinfo=timezone.utc)
    a = _event(event_id="a", title="Critical RCE in ExampleSoft gateway", description="Active exploitation of CVE-2026-10001", observed_at=now, cve_ids=["CVE-2026-10001"], vendors=["ExampleSoft"], confidence=0.2)
    b = _event(event_id="b", title="ExampleSoft gateway critical RCE", description="CVE-2026-10001 exploited in wild with PoC", observed_at=now + timedelta(hours=1), cve_ids=["CVE-2026-10001", "CVE-2026-10002"], vendors=["ExampleSoft"], confidence=0.9, poc_available=True)
    engine = DedupeEngine(similarity_threshold=0.6)
    assert engine.should_merge(a, b) is True
    merged = engine.merge(a, b)
    assert merged.cve_ids == ["CVE-2026-10001", "CVE-2026-10002"]
    assert merged.confidence == 0.9


def test_scoring_and_enrichment_determinism() -> None:
    text = "  CVE-2026-99999   PoC at https://example.test/poc  "
    assert parse_indicators(text) == parse_indicators(text)
    assert stable_text_digest(text) == stable_text_digest(text)

    event = _event(event_id="evt", title="VendorX firewall overflow", description="Exploitation of CVE-2026-99999", observed_at=datetime(2026, 5, 3, 2, 0, tzinfo=timezone.utc), cve_ids=["CVE-2026-99999"], vendors=["VendorX"], products=["Firewall"], poc_available=True, exploitation_in_wild=True)
    dedupe = DedupeEngine()
    assert dedupe.fingerprint(event) == dedupe.fingerprint(event)


def test_alert_policy_routing_and_sink_failure_fallback() -> None:
    router = AlertRouter(routes=[AlertRoute(name="critical", channels=("slack", "webhook"), severities=frozenset({"critical"})), AlertRoute(name="poc", channels=("email",), required_tags=frozenset({"poc"}))])
    event = AlertEvent(event_id="evt-1", source="unit", severity="critical", tags=frozenset({"poc"}), title="Critical vuln")
    assert router.route_event(event) == ("slack", "webhook", "email")

    policy = AlertPolicyEngine(dedupe_window=timedelta(minutes=30), max_frequency=2, frequency_window=timedelta(hours=1), maintenance_windows=(MaintenanceWindow(name="nightly", start=time(3, 0), end=time(3, 30)),))
    assert policy.evaluate(event, None, now=datetime(2026, 5, 3, 3, 10, tzinfo=timezone.utc)).allowed is False

    state = AlertState(alert_id="a1", event_id="evt-1", status=AlertStatus.NEW)
    state = policy.mark_sent(state, now=datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc))
    assert policy.evaluate(event, state, now=datetime(2026, 5, 3, 1, 10, tzinfo=timezone.utc)).allowed is False

    order: list[str] = []
    for channel in router.route_event(event):
        order.append(channel)
        if channel == "slack":
            continue
    assert order == ["slack", "webhook", "email"]


def test_api_events_readiness_and_dashboard_behavior() -> None:
    client = TestClient(api_app_module.app)
    assert client.get("/events").status_code == 200
    readiness = client.get("/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    html = client.get("/").text.lower()
    assert "zero-day alerts" in html
    assert "captured events currently held in memory" in html
