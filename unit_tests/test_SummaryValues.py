from datetime import date

import pandas as pd
import pytest

from osem.MainLoop import (
    holdings_market_value,
    portfolio_market_value,
    remaining_liability_payments,
)


T0 = date(2023, 4, 29)
T1 = date(2024, 4, 29)


@pytest.fixture
def equity_frames():
    price = pd.DataFrame({T0: [10.0, 20.0]}, index=[1, 2])
    units = pd.DataFrame({T0: [3.0, 4.0]}, index=[1, 2])
    return price, units


@pytest.fixture
def bond_frames():
    price = pd.DataFrame({T0: [95.0]}, index=[7])
    units = pd.DataFrame({T0: [2.0]}, index=[7])
    return price, units


def test_holdings_market_value(equity_frames):
    price, units = equity_frames
    assert holdings_market_value(price, units, T0) == pytest.approx(110.0)


def test_portfolio_market_value_adds_equities_and_bonds(equity_frames, bond_frames):
    eq_price, eq_units = equity_frames
    bd_price, bd_units = bond_frames
    assert portfolio_market_value(eq_price, eq_units, bd_price, bd_units, T0) == pytest.approx(300.0)


def test_holdings_market_value_keeps_missing_price_visible(equity_frames):
    price, units = equity_frames
    price.loc[2, T0] = float("nan")
    assert pd.isna(holdings_market_value(price, units, T0))


def test_remaining_liability_payments_adds_all_dates():
    cash_flows = pd.DataFrame({T0: [5.0], T1: [7.0]}, index=[1])
    assert remaining_liability_payments(cash_flows) == pytest.approx(12.0)


def test_remaining_liability_payments_is_zero_when_all_expired():
    cash_flows = pd.DataFrame({T0: [5.0]}, index=[1]).drop(columns=[T0])
    assert remaining_liability_payments(cash_flows) == 0.0
