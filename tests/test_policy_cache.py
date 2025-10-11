from policy import policy_cache


def test_policy_cache_loads_once(tmp_path, monkeypatch):
    # Point POLICY_PATH to a temp file
    policy_text = """
version: 1
slices:
  - id: benign_en
    category: benign
    language: en
    threshold: 1.0
    rules:
      - id: noop
        weight: 1.0
        action: pass
        match:
          regex: ["(?!)"]
"""
    p = tmp_path / "policy.yaml"
    p.write_text(policy_text.strip(), encoding="utf-8")

    # Monkeypatch the default POLICY_PATH used by cache
    from src.policy import compiler as comp
    monkeypatch.setattr(comp, "POLICY_PATH", p)

    policy_cache.clear_cache()
    assert policy_cache.load_count() == 0

    # First load increments counter
    _ = policy_cache.get_compiled_policy()
    assert policy_cache.load_count() == 1

    # Subsequent loads hit cache (mtime unchanged)
    _ = policy_cache.get_compiled_policy()
    _ = policy_cache.get_compiled_policy()
    assert policy_cache.load_count() == 1

    # Touch the file -> bump mtime -> increments on next call
    current = p.read_text(encoding="utf-8")
    p.write_text(current + "\n", encoding="utf-8")
    _ = policy_cache.get_compiled_policy()
    assert policy_cache.load_count() == 2


