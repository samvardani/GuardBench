import sqlite3, pathlib
DB_PATH = pathlib.Path(__file__).resolve().parents[2] / "history.db"

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
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
    CREATE INDEX IF NOT EXISTS idx_results_run_model ON results(run_id, model);
    CREATE INDEX IF NOT EXISTS idx_results_sample ON results(sample_id);
    """)
    con.commit()
    print(f"DB ready at {DB_PATH}")
    con.close()

if __name__ == "__main__":
    main()
