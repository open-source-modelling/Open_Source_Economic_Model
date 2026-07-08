import pandas as pd
import pytest

from SocietyClass import Society


@pytest.fixture
def society() -> Society:
    ages = list(range(0, 5))
    male = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05], index=ages)
    female = pd.Series([0.005, 0.015, 0.025, 0.035, 0.045], index=ages)
    return Society(mortality_male=male, mortality_female=female)


def test_mortality_rate_male(society: Society) -> None:
    assert society.mortality_rate(2, is_female=False) == pytest.approx(0.03)


def test_mortality_rate_female(society: Society) -> None:
    assert society.mortality_rate(1, is_female=True) == pytest.approx(0.015)


def test_age_clamped_low(society: Society) -> None:
    assert society.mortality_rate(-5, is_female=False) == pytest.approx(0.01)


def test_age_clamped_high(society: Society) -> None:
    assert society.mortality_rate(100, is_female=True) == pytest.approx(0.045)
