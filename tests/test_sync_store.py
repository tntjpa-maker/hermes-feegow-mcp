from ana_feegow.webhooks.sync_store import SyncStore


def test_store_mapeia_e_deduplica(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_mapping("uid-1", 10, 321, "scheduled")
    mapping = store.get_mapping("uid-1")
    assert mapping["feegow_appointment_id"] == 321

    store.mark_event("event-1", "BOOKING_PAID", "uid-1")
    assert store.event_processed("event-1") is True
