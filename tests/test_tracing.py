from dont_be_a_dick import tracing


def test_session_is_a_no_op_when_tracing_is_off(monkeypatch) -> None:
    monkeypatch.setattr(tracing.langfuse_settings.__class__, "active", property(lambda _: False))

    with tracing.session("lula:1"):
        pass

    assert tracing.callbacks() == []
