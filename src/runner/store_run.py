import csv, json, sqlite3, pathlib, datetime
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt

from src.guards.baseline import predict as predict_baseline
from src.guards.candidate import predict as predict_candidate
from src.utils.io_utils import load_config, resolve_dataset_path, sha256_file, git_commit, new_run_id

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "history.db"
TPL_DIR = ROOT / "templates"
OUT_DIR = ROOT / "report"
ASSETS = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def ensure_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      created_at TEXT,
      dataset_path TEXT,
      dataset_sha TEXT,
      git_commit TEXT,
      policy_version TEXT,
      engine_baseline TEXT,
      engine_candidate TEXT
    );
    CREATE TABLE IF NOT EXISTS metrics (
      run_id TEXT,
      model TEXT,
      tp INTEGER, fp INTEGER, tn INTEGER, fn INTEGER,
      precision REAL, recall REAL, fnr REAL, fpr REAL,
      p50_ms INTEGER, p90_ms INTEGER, p99_ms INTEGER,
      PRIMARY KEY (run_id, model)
    );
    CREATE TABLE IF NOT EXISTS results (
      run_id TEXT,
      sample_id TEXT,
      model TEXT,
      gt_label TEXT,
      gt_category TEXT,
      gt_language TEXT,
      attack_type TEXT,
      prediction TEXT,
      score REAL,
      latency_ms INTEGER
    );
    """)
    con.commit()
    return con

def load_rows(path):
    rows=[]; 
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

def run_guard(rows, fn):
    preds=[]; lats=[]
    for r in rows:
        out = fn(r["text"])
        preds.append(out); lats.append(out.get("latency_ms",0))
    return preds, lats

def confusion(rows, preds):
    cm = Counter()
    for r,p in zip(rows,preds):
        gt_pos = (r["label"].strip().lower() != "benign")
        pr_pos = (p["prediction"] == "flag")
        if gt_pos and pr_pos: cm["tp"] += 1
        elif (not gt_pos) and pr_pos: cm["fp"] += 1
        elif (not gt_pos) and (not pr_pos): cm["tn"] += 1
        elif gt_pos and (not pr_pos): cm["fn"] += 1
    tp,fp,tn,fn = cm["tp"],cm["fp"],cm["tn"],cm["fn"]
    def pct(a,b): return round(a/b,3) if b else 0.0
    return {
        "tp":tp,"fp":fp,"tn":tn,"fn":fn,
        "precision": pct(tp, tp+fp),
        "recall":    pct(tp, tp+fn),
        "fnr":       pct(fn, tp+fn),
        "fpr":       pct(fp, fp+tn),
    }

def pctiles(values):
    if not values: return {"p50":0,"p90":0,"p99":0}
    vs = sorted(values)
    def p(q): return vs[int((len(vs)-1)*q)]
    return {"p50":p(0.50),"p90":p(0.90),"p99":p(0.99)}

def histogram(values, out_png, title):
    if not values: values=[0]
    import matplotlib.pyplot as plt
    plt.figure()
    plt.hist(values, bins=min(10, max(3, len(set(values)))))
    plt.title(title); plt.xlabel("Latency (ms)"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_png); plt.close()

def main():
    cfg = load_config()
    dataset_path = resolve_dataset_path(cfg)
    rows = load_rows(dataset_path)
    run_id = new_run_id()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ds_sha = sha256_file(dataset_path)
    commit = git_commit()

    base_preds, base_lat = run_guard(rows, predict_baseline)
    cand_preds, cand_lat = run_guard(rows, predict_candidate)
    base_cm = confusion(rows, base_preds)
    cand_cm = confusion(rows, cand_preds)
    base_lat_pct = pctiles(base_lat)
    cand_lat_pct = pctiles(cand_lat)

    # charts
    base_png = ASSETS / f"latency_baseline_{run_id}.png"
    cand_png = ASSETS / f"latency_candidate_{run_id}.png"
    histogram(base_lat, base_png, "Baseline latency")
    histogram(cand_lat, cand_png, "Candidate latency")

    # store in DB
    con = ensure_db(); cur = con.cursor()
    cur.execute("""INSERT INTO runs(run_id,created_at,dataset_path,dataset_sha,git_commit,policy_version,engine_baseline,engine_candidate)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (run_id, created_at, str(dataset_path), ds_sha, commit, cfg.get("policy_version","n/a"),
                 cfg["engines"]["baseline"]["name"], cfg["engines"]["candidate"]["name"]))
    for name, cm, lat in [("Baseline", base_cm, base_lat_pct), ("Candidate", cand_cm, cand_lat_pct)]:
        cur.execute("""INSERT INTO metrics(run_id,model,tp,fp,tn,fn,precision,recall,fnr,fpr,p50_ms,p90_ms,p99_ms)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, name, cm["tp"], cm["fp"], cm["tn"], cm["fn"],
                     cm["precision"], cm["recall"], cm["fnr"], cm["fpr"],
                     lat["p50"], lat["p90"], lat["p99"]))
    for model_name, preds in [("Baseline", base_preds), ("Candidate", cand_preds)]:
        for r,p in zip(rows, preds):
            cur.execute("""INSERT INTO results(run_id,sample_id,model,gt_label,gt_category,gt_language,attack_type,prediction,score,latency_ms)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (run_id, r["id"], model_name, r["label"], r["category"], r["language"], r["attack_type"],
                         p.get("prediction"), float(p.get("score", 0.0)), int(p.get("latency_ms", 0))))
    con.commit(); con.close()

    # render HTML + metrics JSON (with this same run_id)
    env = Environment(loader=FileSystemLoader(TPL_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(
        run_title="Baseline vs Candidate",
        run_id=run_id,
        dataset_path=str(dataset_path),
        dataset_sha=ds_sha,
        total_samples=len(rows),
        generated_at=created_at,
        policy_version=cfg.get("policy_version","n/a"),
        engines={"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        metrics={
          "Baseline":{"precision":base_cm["precision"],"recall":base_cm["recall"],"fnr":base_cm["fnr"],"fpr":base_cm["fpr"],"latency":base_lat_pct},
          "Candidate":{"precision":cand_cm["precision"],"recall":cand_cm["recall"],"fnr":cand_cm["fnr"],"fpr":cand_cm["fpr"],"latency":cand_lat_pct}
        },
        matrices={"Baseline":base_cm, "Candidate":cand_cm},
        latency_imgs={"baseline":str(base_png.relative_to(ROOT)), "candidate":str(cand_png.relative_to(ROOT))},
        downloads={"fn_csv":"report/candidate_fn.csv", "fp_csv":"report/candidate_fp.csv"},
        failures=[]  # keeping simple for store_run; build_report already has detailed exports
    )
    out_html = OUT_DIR / f"index_{run_id}.html"
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    out_html.write_text(html, encoding="utf-8")

    metrics_json = {
        "run_id": run_id, "generated_at": created_at,
        "dataset_path": str(dataset_path), "dataset_sha256": ds_sha,
        "git_commit": commit, "policy_version": cfg.get("policy_version","n/a"),
        "engines": {"baseline":cfg["engines"]["baseline"]["name"], "candidate":cfg["engines"]["candidate"]["name"]},
        "metrics": {"Baseline": base_cm, "Candidate": cand_cm}
    }
    out_json = OUT_DIR / f"metrics_{run_id}.json"
    with open(out_json,"w",encoding="utf-8") as f: json.dump(metrics_json, f, ensure_ascii=False, indent=2)

    print(f"Stored run {run_id} → DB: {DB_PATH}")
    print(f"Report: {out_html}")
    print(f"Metrics JSON: {out_json}")

if __name__ == "__main__":
    main()
