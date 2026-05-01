from src.storage.raw_event_store import InMemoryRawEventStore, RawEvent
from src.workers.scheduler import CollectorScheduler


def test_run_collectors_writes_events() -> None:
    store = InMemoryRawEventStore()

    def collector() -> list[RawEvent]:
        return [RawEvent(source="unit", title="event", payload={"id": 1})]

    scheduler = CollectorScheduler(collectors=[collector], store=store)

    scheduler._run_collectors()

    assert store.count() == 1
