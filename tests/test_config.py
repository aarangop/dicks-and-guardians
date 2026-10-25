import os

from dont_be_a_dick.config import PROJECT_ROOT, LangfuseSettings, Settings


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


def test_langfuse_settings_are_separate_from_app_settings(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.delenv("DBAD_PUBLIC_KEY", raising=False)

    assert LangfuseSettings(_env_file=None).public_key == "pk-test"  # type: ignore[call-arg]
    assert not hasattr(Settings(_env_file=None), "public_key")  # type: ignore[call-arg]


def test_tracing_needs_the_flag_and_both_keys(monkeypatch) -> None:
    # the app exports `.env` into the environment at import, so clear any real keys first
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_TRACING_ENABLED"):
        monkeypatch.delenv(name, raising=False)

    def make_langfuse(**kw):
        return LangfuseSettings(_env_file=None, **kw)  # type: ignore[call-arg]

    assert not make_langfuse(public_key="pk", secret_key="sk").active
    assert not make_langfuse(tracing_enabled=True, public_key="pk").active
    assert make_langfuse(tracing_enabled=True, public_key="pk", secret_key="sk").active


def test_export_does_not_override_the_real_environment(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://real.example")
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    settings = LangfuseSettings(  # type: ignore[call-arg]
        _env_file=None, base_url="https://other.example", tracing_environment="eval"
    )

    settings.export_to_environ()

    assert os.environ["LANGFUSE_BASE_URL"] == "https://real.example"
    assert os.environ["LANGFUSE_TRACING_ENVIRONMENT"] == "eval"
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT")


def test_research_budget_is_configurable() -> None:
    settings = make(research_max_searches="20", research_max_fetches="8")

    assert (settings.research_max_searches, settings.research_max_fetches) == (20, 8)


def test_env_file_and_database_do_not_depend_on_the_working_directory(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)

    assert Settings(_env_file=None).db_path.is_absolute()  # type: ignore[call-arg]
    assert (PROJECT_ROOT / "pyproject.toml").exists()
    assert Settings(_env_file=None).db_path == PROJECT_ROOT / "data" / "results.json"  # type: ignore[call-arg]
