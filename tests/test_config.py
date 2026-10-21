import os

from dont_be_a_dick.config import LangSmithSettings, Settings


def make(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_every_role_falls_back_to_the_default_model() -> None:
    settings = make(default_model="some-model")

    for role in ("researcher", "judge", "resolver", "summarizer", "chat"):
        assert settings.model_for(role) == "some-model"  # type: ignore[arg-type]


def test_a_role_override_changes_only_that_role() -> None:
    settings = make(default_model="some-model", judge_model="judge-model")

    assert settings.model_for("judge") == "judge-model"
    assert settings.model_for("researcher") == "some-model"


def test_langsmith_settings_are_separate_from_app_settings(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_PROJECT", "my-project")
    monkeypatch.delenv("DBAD_PROJECT", raising=False)

    assert LangSmithSettings(_env_file=None).project == "my-project"  # type: ignore[call-arg]
    assert not hasattr(Settings(_env_file=None), "project")  # type: ignore[call-arg]


def test_export_does_not_override_the_real_environment(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://real.example")
    monkeypatch.delenv("LANGSMITH_AGENT_ID", raising=False)
    settings = LangSmithSettings(  # type: ignore[call-arg]
        _env_file=None, endpoint="https://other.example", agent_id="agent-1"
    )

    settings.export_to_environ()

    assert os.environ["LANGSMITH_ENDPOINT"] == "https://real.example"
    assert os.environ["LANGSMITH_AGENT_ID"] == "agent-1"
    monkeypatch.delenv("LANGSMITH_AGENT_ID")


def test_research_budget_is_configurable() -> None:
    settings = make(research_max_searches="20", research_max_fetches="8")

    assert (settings.research_max_searches, settings.research_max_fetches) == (20, 8)
