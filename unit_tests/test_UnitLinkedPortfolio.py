from datetime import date

import pytest

from LiabilityClasses import UnitLinkedPolicy, UnitLinkedPortfolio


@pytest.fixture
def portfolio() -> UnitLinkedPortfolio:
    p1 = UnitLinkedPolicy(
        policy_id=1001,
        birth_date=date(1970, 3, 15),
        is_female=True,
        is_guaranteed=False,
        premium=5000.0,
        mv=120000.0,
        gv=0.0,
    )
    p2 = UnitLinkedPolicy(
        policy_id=1002,
        birth_date=date(1965, 7, 22),
        is_female=False,
        is_guaranteed=True,
        premium=8000.0,
        mv=250000.0,
        gv=200000.0,
    )
    return UnitLinkedPortfolio({p1.policy_id: p1, p2.policy_id: p2})


def test_is_empty() -> None:
    assert UnitLinkedPortfolio().IsEmpty() is True


def test_add_and_not_empty(portfolio: UnitLinkedPortfolio) -> None:
    assert portfolio.IsEmpty() is False
    extra = UnitLinkedPolicy(
        policy_id=1003,
        birth_date=date(1980, 1, 10),
        is_female=True,
        is_guaranteed=False,
        premium=3000.0,
        mv=75000.0,
        gv=0.0,
    )
    portfolio.add(extra)
    assert 1003 in portfolio.policies


def test_init_policy_state_to_dataframe(portfolio: UnitLinkedPortfolio) -> None:
    modelling_date = date(2023, 4, 29)
    mv_df, gv_df, premium_df, active_df = portfolio.init_policy_state_to_dataframe(modelling_date)

    assert list(mv_df.index) == [1001, 1002]
    assert mv_df.loc[1001, modelling_date] == 120000.0
    assert gv_df.loc[1002, modelling_date] == 200000.0
    assert premium_df.loc[1001, modelling_date] == 5000.0
    assert active_df.loc[1001, modelling_date] == 1.0


def test_total_reserve(portfolio: UnitLinkedPortfolio) -> None:
    modelling_date = date(2023, 4, 29)
    mv_df, _, _, active_df = portfolio.init_policy_state_to_dataframe(modelling_date)
    assert portfolio.total_reserve(mv_df, active_df, modelling_date) == 370000.0

    active_df.loc[1001, modelling_date] = 0.0
    assert portfolio.total_reserve(mv_df, active_df, modelling_date) == 250000.0
