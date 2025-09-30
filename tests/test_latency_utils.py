
from src.runner.ci_gate import ptiles

def test_ptiles_quantiles():
    vals = [0, 1, 2, 10, 20, 100]
    qs = ptiles(vals)
    assert qs["p50"] in vals
    assert qs["p90"] in vals
    assert qs["p99"] in vals
