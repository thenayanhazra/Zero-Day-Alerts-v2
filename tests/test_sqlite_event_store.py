from src.storage.raw_event_store import ProcessedEvent, RawEvent, SQLiteEventStore


def test_sqlite_raw_event_uniqueness(tmp_path) -> None:
    store = SQLiteEventStore(str(tmp_path / "events.db"))
    event = RawEvent(source="unit", title="duplicate", payload={"id": 1})

    first = store.write_many([event])
    second = store.write_many([event])

    assert first == 1
    assert second == 0
    assert store.count() == 1


def test_sqlite_processed_event_crud(tmp_path) -> None:
    store = SQLiteEventStore(str(tmp_path / "events.db"))
    event = ProcessedEvent(event_id="e-1", source="unit", title="normalized", payload={"sev": "high"})

    store.upsert_processed_event(event)
    fetched = store.get_processed_event("e-1")
    assert fetched is not None
    assert fetched.title == "normalized"

    updated = ProcessedEvent(
        event_id="e-1",
        source="unit",
        title="normalized-updated",
        payload={"sev": "critical"},
        status="triaged",
    )
    store.upsert_processed_event(updated)

    listed = store.list_processed_events()
    assert len(listed) == 1
    assert listed[0].status == "triaged"

    assert store.delete_processed_event("e-1") is True
    assert store.get_processed_event("e-1") is None
