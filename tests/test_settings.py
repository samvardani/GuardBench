from service.settings import Settings


def test_settings_defaults_no_env(tmp_path, monkeypatch):
    # Ensure no .env in CWD
    monkeypatch.chdir(tmp_path)
    s = Settings()  # type: ignore[call-arg]
    assert s.predict_max_workers >= 1
    assert isinstance(s.rate_limit_enabled, bool)
    assert s.redis_url is None


def test_settings_env_file(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("""
PREDICT_MAX_WORKERS=42
RATE_LIMIT_ENABLED=false
REDIS_URL=redis://localhost:6379/0
""".strip(), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    # Ensure process env does not override .env for these keys
    monkeypatch.delenv("PREDICT_MAX_WORKERS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    s = Settings()  # type: ignore[call-arg]
    assert s.predict_max_workers == 42
    assert s.rate_limit_enabled is False
    assert s.redis_url == "redis://localhost:6379/0"

