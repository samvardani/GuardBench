
from runner.ci_gate import ptiles

def test_ptiles_empty():
    assert ptiles([]) == {"p50":0,"p90":0,"p99":0}
