"""Regression coverage for shared fitter/assist quantity normalization."""

import pytest

from resume_renderer.services.line_fitter import _number_inventory


@pytest.mark.parametrize(
    "compact,expanded",
    [
        ("5k+ users", "5,000+ users"),
        ("5K users", "5000 users"),
        ("1.25k records", "1250 records"),
        ("1.2345k records", "1234.5 records"),
        ("100k records", "100000 records"),
        ("5 thousand users", "5000 users"),
        ("1.2 million records", "1200000 records"),
        ("2 lakh records", "200000 records"),
    ],
)
def test_equivalent_magnitudes_have_identical_inventory(compact, expanded):
    assert _number_inventory(compact) == _number_inventory(expanded)


def test_wrong_scale_does_not_match():
    assert _number_inventory("5k users") != _number_inventory("50,000 users")
