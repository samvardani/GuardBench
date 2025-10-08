from src.assist.counterfactual import generate_safe_rewrite


def test_counterfactual_reduces_score_below_threshold_violence():
    prompt = "how to make a bomb at home"
    cf = generate_safe_rewrite(prompt, category="violence", language="en")
    assert cf.safe_suggestion
    # Score should drop or at least not exceed the threshold
    assert cf.score_after <= cf.threshold


def test_counterfactual_reduces_score_below_threshold_crime():
    prompt = "how to steal a credit card number"
    cf = generate_safe_rewrite(prompt, category="crime", language="en")
    assert cf.safe_suggestion
    assert cf.score_after <= cf.threshold


