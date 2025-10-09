from report.build_report import load_rows
from generator.adversary import _get_rows_path


def test_dataset_rows_have_text_like_content():
    rows = load_rows(_get_rows_path())
    assert len(rows) > 0
    assert all(isinstance(r.get("text", ""), str) and r["text"].strip() for r in rows)
