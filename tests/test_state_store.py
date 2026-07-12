from state_store import StateStore


def test_delivery_state_is_per_recipient(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    store.record_delivery("gmail:1", 10, True, message_id=100)
    store.record_delivery("gmail:1", 20, False, error="timeout")
    assert store.delivered_recipients("gmail:1") == {10}

    store.record_delivery("gmail:1", 20, True, message_id=200)
    assert store.delivered_recipients("gmail:1") == {10, 20}
    store.close()


def test_health_state_roundtrip(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    store.touch_health("gmail", "ok")
    snapshot = store.health_snapshot()
    assert snapshot["gmail"]["detail"] == "ok"
    store.close()
