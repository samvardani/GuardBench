"""Demo test to verify GitHub Actions workflow."""

def test_github_actions_works():
    """Verify GitHub Actions can run tests."""
    assert True, "GitHub Actions is working!"


def test_coverage_tracking():
    """Verify coverage is tracked."""
    result = 2 + 2
    assert result == 4, "Math works!"


def test_searai_branding():
    """Verify SeaRai branding is correct."""
    company = "SeaTechOne LLC"
    product = "SeaRai"
    
    assert company == "SeaTechOne LLC"
    assert product == "SeaRai"

