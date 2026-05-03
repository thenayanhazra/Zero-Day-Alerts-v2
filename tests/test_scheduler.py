from src.storage.raw_event_store import InMemoryRawEventStore, RawEvent
from src.workers.scheduler import CollectorScheduler


def test_run_collectors_writes_events() -> None:
    store = InMemoryRawEventStore()

    def collector() -> list[RawEvent]:
        return [RawEvent(source="unit", title="event", payload={"id": 1})]

    scheduler = CollectorScheduler(collectors=[collector], raw_store=store)

    scheduler._run_collectors()

    assert store.count() == 1


def test_run_collectors_continues_when_one_collector_fails() -> None:
    store = InMemoryRawEventStore()

    def failing_collector() -> list[RawEvent]:
        raise RuntimeError("boom")

    def passing_collector() -> list[RawEvent]:
        return [RawEvent(source="unit", title="event", payload={"id": 2})]

    scheduler = CollectorScheduler(collectors=[failing_collector, passing_collector], raw_store=store)

    scheduler._run_collectors()

    assert store.count() == 1


def test_start_rejects_non_positive_interval() -> None:
    scheduler = CollectorScheduler(collectors=[], raw_store=InMemoryRawEventStore())

    try:
        scheduler.start(interval_seconds=0)
    except ValueError as exc:
        assert "greater than zero" in str(exc)
    else:
        raise AssertionError("expected ValueError")
