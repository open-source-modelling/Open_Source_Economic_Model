from datetime import date

import pytest

from LiabilityClasses import UnitLinkedPolicy


@pytest.fixture
def sample_policy() -> UnitLinkedPolicy:
    return UnitLinkedPolicy(
        policy_id=1001,
        birth_date=date(1970, 3, 15),
        is_female=True,
        is_guaranteed=False,
        premium=5000.0,
        mv=120000.0,
        gv=0.0,
    )


def test_construct(sample_policy: UnitLinkedPolicy) -> None:
    assert sample_policy.policy_id == 1001
    assert sample_policy.birth_date == date(1970, 3, 15)
    assert sample_policy.is_female is True
    assert sample_policy.is_guaranteed is False
    assert sample_policy.premium == 5000.0
    assert sample_policy.mv == 120000.0
    assert sample_policy.gv == 0.0


def test_age_at(sample_policy: UnitLinkedPolicy) -> None:
    assert sample_policy.age_at(date(2023, 4, 29)) == 53


def test_invalid_policy_id() -> None:
    with pytest.raises(ValueError):
        UnitLinkedPolicy(
            policy_id=0,
            birth_date=date(1970, 3, 15),
            is_female=True,
            is_guaranteed=False,
            premium=5000.0,
            mv=120000.0,
            gv=0.0,
        )


def test_negative_mv() -> None:
    with pytest.raises(ValueError):
        UnitLinkedPolicy(
            policy_id=1,
            birth_date=date(1970, 3, 15),
            is_female=True,
            is_guaranteed=False,
            premium=5000.0,
            mv=-1.0,
            gv=0.0,
        )
