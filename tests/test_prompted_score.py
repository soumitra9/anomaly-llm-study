"""Mode-B numeric helpers: expected-value scorer (tie-free) + integer-parse fallback."""
import numpy as np

from src.scoring.prompted_score import expected_score, parse_failure_rate, parse_int_score


def test_expected_score_mass_and_uniform():
    levels = list(range(11))
    lp = np.full(11, -50.0)
    lp[10] = 0.0  # essentially all mass on level 10
    assert abs(expected_score(levels, lp) - 10) < 1e-6
    assert abs(expected_score(levels, np.zeros(11)) - 5) < 1e-9  # uniform -> mean 5


def test_expected_score_is_monotone_in_logprob_mass():
    levels = [0, 50, 100]
    low = expected_score(levels, [0, -1, -5])    # mass low
    high = expected_score(levels, [-5, -1, 0])   # mass high
    assert high > low


def test_parse_int_score_cases():
    assert parse_int_score("Score: 87") == 87
    assert parse_int_score("87/100") == 87
    assert parse_int_score("The anomaly rating is 42.") == 42
    assert parse_int_score("score 150 or 73") == 73   # first IN-RANGE integer
    assert parse_int_score("eighty-seven") is None
    assert parse_int_score("") is None
    assert parse_int_score("999", 0, 100) is None       # out of range -> failure


def test_parse_failure_rate():
    assert parse_failure_rate([1, None, 3, None]) == 0.5
