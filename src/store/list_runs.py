import sqlite3
import pathlib
DB_PATH = pathlib.Path(__file__).resolve().parents[2] / "history.db"

def main():
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    cur.execute("""
      SELECT r.run_id, r.created_at, substr(r.dataset_sha,1,12)||'…',
             m.model, m.precision, m.recall, m.fnr
      FROM runs r
      JOIN metrics m ON m.run_id = r.run_id
      ORDER BY r.created_at DESC, m.model ASC
      LIMIT 20
    """)
    rows = cur.fetchall()
    if not rows:
        print("No runs found."); return
    # pretty print
    current = None
    for run_id, ts, sha, model, prec, rec, fnr in rows:
        if run_id != current:
            print(f"\nRun {run_id}  @ {ts}  (SHA {sha})")
            current = run_id
        print(f"  {model:<9}  precision={prec:.3f}  recall={rec:.3f}  fnr={fnr:.3f}")
    con.close()

if __name__ == "__main__":
    main()
