import json
import hashlib
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from service import api, db
from src.autopatch import run as autopatch_run
from src.autopatch import candidates


def _hash_updates(updates):
    return hashlib.sha256(json.dumps(updates, sort_keys=True).encode("utf-8")).hexdigest()


@pytest.fixture
def service_env(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    tuned_path = tmp_path / "tuned_thresholds.yaml"
    canary_path = tmp_path / "tuned_thresholds_canary.yaml"
    rollback_dir = tmp_path / "rollbacks"

    config_path.write_text(
        yaml.safe_dump(
            {
                "policy_version": "v1.0",
                "slice_thresholds": {"self_harm": {"en": 5.0}},
                "tenants": {"tenant": {"autopatch_canary": True}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    tuned_path.write_text(
        yaml.safe_dump({"slice_thresholds": {"self_harm": {"en": 5.0}}}, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(api, "CONFIG_FILE", config_path)
    monkeypatch.setattr(api, "AUTOPATCH_THRESHOLD_PATH", tuned_path)
    monkeypatch.setattr(api, "AUTOPATCH_CANARY_PATH", canary_path)
    monkeypatch.setattr(api, "AUTOPATCH_ROLLBACK_DIR", rollback_dir)
    monkeypatch.setattr(api, "_run_offline_ab_check", lambda payload: (True, "stub"))
    monkeypatch.setattr(api, "_run_shadow_check", lambda payload: (True, "stub"))
    monkeypatch.setattr(api.db, "create_audit_event", lambda *args, **kwargs: None)

    db_path = tmp_path / "history.db"
    from src.store import init_db as store_init_db

    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(store_init_db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "_SCHEMA_READY", False)
    db.ensure_schema()

    tenant = db.create_tenant("Tenant", slug="tenant")
    db.set_autopatch_canary_flag(tenant["tenant_id"], True)

    def _auth(role: str = "admin"):
        return api.AuthContext(
            token="token",
            tenant_id=tenant["tenant_id"],
            tenant_slug="tenant",
            user_id="user",
            email="owner@example.com",
            role=role,
        )

    monkeypatch.setattr(api, "_auth_from_token", lambda token: _auth("admin"))

    return {
        "config_path": config_path,
        "tuned_path": tuned_path,
        "canary_path": canary_path,
        "rollback_dir": rollback_dir,
        "tenant": tenant,
        "auth_factory": _auth,
    }


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_autopatch_promotion_and_rollback(service_env):
    client = TestClient(api.app)
    updates = {"self_harm/en": 4.4}
    signature = _hash_updates(updates)
    service_env["canary_path"].write_text(
        yaml.safe_dump(
            {
                "tenant": "tenant",
                "generated_at": "2024-01-01T00:00:00Z",
                "threshold_updates": updates,
                "signature": signature,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    promote = client.post("/autopatch/promote", headers={"Authorization": "Bearer token"})
    assert promote.status_code == 200
    payload = promote.json()
    assert payload["status"] == "promoted"

    tuned = _load_yaml(service_env["tuned_path"])
    assert tuned["slice_thresholds"]["self_harm"]["en"] == 4.4

    cfg = _load_yaml(service_env["config_path"])
    assert cfg["policy_version"] == "v1.1"

    manifests = list(service_env["rollback_dir"].glob("*.json"))
    assert len(manifests) == 1

    status_resp = client.get("/autopatch/status", headers={"Authorization": "Bearer token"})
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["autopatch_canary"] is True
    assert status_data["pending_promotion"] is False
    assert status_data["rollbacks"], "Expected rollbacks list"

    rollback = client.post("/autopatch/rollback", headers={"Authorization": "Bearer token"})
    assert rollback.status_code == 200
    rollback_data = rollback.json()
    assert rollback_data["status"] == "rolled_back"

    tuned_after = _load_yaml(service_env["tuned_path"])
    assert tuned_after["slice_thresholds"]["self_harm"]["en"] == 5.0

    cfg_after = _load_yaml(service_env["config_path"])
    assert cfg_after["policy_version"] == "v1.0"


def test_autopatch_promotion_blocked_when_checks_fail(service_env, monkeypatch):
    client = TestClient(api.app)
    updates = {"self_harm/en": 4.2}
    service_env["canary_path"].write_text(
        yaml.safe_dump(
            {
                "tenant": "tenant",
                "generated_at": "2024-01-01T00:00:00Z",
                "threshold_updates": updates,
                "signature": _hash_updates(updates),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(api, "_run_offline_ab_check", lambda payload: (False, "delta too small"))

    resp = client.post("/autopatch/promote", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 400
    assert "Offline A/B" in resp.json()["detail"]


def test_autopatch_run_writes_canary(tmp_path, monkeypatch):
    canary_path = tmp_path / "tuned_thresholds_canary.yaml"

    monkeypatch.setattr(autopatch_run, "CANARY_PATH", canary_path)
    monkeypatch.setattr(autopatch_run, "load_config", lambda: {"tenants": {"default": {"autopatch_canary": True}}})

    candidate = candidates.CandidatePatch(
        id="threshold::self_harm/en",
        type="threshold",
        description="lower threshold",
        target_slices=["self_harm/en"],
        data={"self_harm/en": 4.5},
        score=1.0,
    )

    monkeypatch.setattr(
        autopatch_run.candidates,
        "generate_candidates",
        lambda *args, **kwargs: {"threshold": [candidate], "regex": [], "prompt": [], "cases": []},
    )
    monkeypatch.setattr(
        autopatch_run.ab_eval,
        "evaluate_threshold_candidate",
        lambda *args, **kwargs: {
            "delta": {"recall": 0.1, "fpr": -0.001},
            "per_slice": {"self_harm/en": {"delta": {"recall": 0.1, "fpr": -0.001}}},
        },
    )
    monkeypatch.setattr(autopatch_run.ab_eval, "accepts_improvement", lambda result, slices: True)
    monkeypatch.setattr(autopatch_run.ab_eval, "DEFAULT_RESULT_PATH", tmp_path / "ab_result.json")
    monkeypatch.setattr(autopatch_run.pr_bot, "generate_pr_bundle", lambda **kwargs: tmp_path / "PR_BODY.md")

    cases_file = tmp_path / "cases.jsonl"
    cases_file.write_text("{}\n", encoding="utf-8")

    result = autopatch_run.main([
        "--target",
        "self_harm/en",
        "--tenant",
        "default",
        "--cases",
        str(cases_file),
    ])
    assert result == 0
    assert canary_path.exists()
    canary = yaml.safe_load(canary_path.read_text(encoding="utf-8"))
    assert canary["tenant"] == "default"
    assert canary["threshold_updates"] == {"self_harm/en": 4.5}
    assert canary.get("signature") == _hash_updates({"self_harm/en": 4.5})
