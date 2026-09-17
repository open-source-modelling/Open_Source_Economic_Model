from datetime import date

import pandas as pd
import pytest

from osem.MainLoop import (
    find_terminated_positions,
    liquidate_positions,
    process_expired_cf,
    portfolio_market_value,
    trade,
)

PREVIOUS = date(2073, 4, 16)
CURRENT = date(2074, 4, 16)
TERMINAL = date(2074, 4, 10)


@pytest.fixture
def ter_df() -> pd.DataFrame:
    # Asset 1 has a terminal flow in this period, asset 2 has none (zero row),
    # asset 3 terminates in a later period.
    later = date(2080, 1, 1)
    return pd.DataFrame(
        data=[[110.0, 0.0], [0.0, 0.0], [0.0, 55.0]],
        index=[1, 2, 3],
        columns=[TERMINAL, later],
    )


@pytest.fixture
def eq_units() -> pd.DataFrame:
    return pd.DataFrame(
        data=[[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]],
        index=[1, 2, 3],
        columns=[PREVIOUS, CURRENT],
    )


def test_find_terminated_positions(ter_df):
    unique_dates = list(ter_df.columns)
    assert find_terminated_positions(unique_dates, CURRENT, ter_df) == [1]


def test_find_terminated_positions_none_expired(ter_df):
    unique_dates = list(ter_df.columns)
    assert find_terminated_positions(unique_dates, PREVIOUS, ter_df) == []


def test_liquidate_positions(eq_units):
    eq_units = liquidate_positions(eq_units, [1], CURRENT)
    assert eq_units.loc[1, CURRENT] == 0.0
    assert eq_units.loc[2, CURRENT] == 20.0
    assert eq_units.loc[3, CURRENT] == 30.0
    # Earlier dates are untouched
    assert eq_units.loc[1, PREVIOUS] == 10.0


def test_liquidate_positions_empty(eq_units):
    expected = eq_units.copy()
    eq_units = liquidate_positions(eq_units, [], CURRENT)
    pd.testing.assert_frame_equal(eq_units, expected)


def test_terminal_value_not_double_counted():
    """
    Regression test: an equity whose terminal value is paid into the bank account must
    be removed from the portfolio, so trade() does not reinvest the proceeds on top of
    the still-held position (which doubled End market value at the end of the run).
    """
    eq_price = pd.DataFrame(data=[[100.0, 110.0]], index=[1], columns=[PREVIOUS, CURRENT])
    eq_units = pd.DataFrame(data=[[10.0, 10.0]], index=[1], columns=[PREVIOUS, CURRENT])
    bd_price = pd.DataFrame(columns=[PREVIOUS, CURRENT], dtype=float)
    bd_units = pd.DataFrame(columns=[PREVIOUS, CURRENT], dtype=float)
    bank_account = pd.DataFrame(data=[[0.0, 0.0]], columns=[PREVIOUS, CURRENT])
    ter_df = pd.DataFrame(data=[[110.0]], index=[1], columns=[TERMINAL])
    unique_ter_dates = [TERMINAL]

    after_growth_mv = portfolio_market_value(eq_price, eq_units, bd_price, bd_units, CURRENT)
    assert after_growth_mv == pytest.approx(1100.0)

    terminated_ids = find_terminated_positions(unique_ter_dates, CURRENT, ter_df)
    cash, ter_df, unique_ter_dates = process_expired_cf(unique_ter_dates, CURRENT, ter_df, eq_units)
    bank_account[CURRENT] += cash
    assert cash == pytest.approx(1100.0)
    assert unique_ter_dates == []

    eq_units = liquidate_positions(eq_units, terminated_ids, CURRENT)
    eq_units, bd_units, bank_account = trade(CURRENT, bank_account, eq_units, eq_price, bd_units, bd_price)

    end_mv = portfolio_market_value(eq_price, eq_units, bd_price, bd_units, CURRENT)
    end_cash = float(bank_account.loc[0, CURRENT])

    # Value moved from market value into cash, not duplicated
    assert end_mv == pytest.approx(0.0)
    assert end_cash == pytest.approx(1100.0)
    assert end_mv + end_cash == pytest.approx(after_growth_mv)
