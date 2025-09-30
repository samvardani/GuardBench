import importlib
import hashlib
import subprocess
import uuid
from pathlib import Path

_yaml_spec = importlib.util.find_spec("yaml")
if _yaml_spec is not None:
    yaml = importlib.import_module("yaml")
else:
    from . import simple_yaml as yaml

ROOT = Path(__file__).resolve().parents[2]

def load_config():
    with open(ROOT / "config.yaml","r") as f:
        return yaml.safe_load(f)

def resolve_dataset_path(cfg):
    raw = cfg.get("dataset_path", "./dataset/sample.csv")
    p = Path(raw)
    if not p.is_absolute():
        p = (ROOT / raw).resolve()
    return p

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def git_commit() -> str:
    try:
        out = subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT).decode().strip()
        return out
    except Exception:
        return "unknown"

def new_run_id() -> str:
    return uuid.uuid4().hex[:8]
