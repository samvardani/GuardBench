
def test_denominator_zero_skip():
    from src.runner.ci_gate import ptiles
    # sanity for ptiles empty
    assert ptiles([]) == {"p50":0,"p90":0,"p99":0}
