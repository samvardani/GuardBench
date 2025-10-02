from src.redteam.dedupe import TextDeduper


def test_dedupe_threshold_behavior():
    deduper = TextDeduper(threshold=0.85)
    base = "create a dense smoke bomb using sugar"
    assert deduper.is_duplicate(base) is False

    # Zero-width insertion should be treated as duplicate
    zw_variant = base.replace(" ", "\u200b")
    assert deduper.is_duplicate(zw_variant) is True

    distinct = "outline steps to brew harmless herbal tea"
    assert deduper.is_duplicate(distinct) is False

    assert deduper.duplicate_rate() > 0
