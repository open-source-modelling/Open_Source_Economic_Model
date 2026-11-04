from datetime import date

import numpy as np
import pandas as pd
import pytest

from osem.BondClasses import CorpBond, BondPortfolio
from osem.FrequencyClass import Frequency
from osem.MainLoop import (
    assets_exhausted,
    create_cashflow_dataframe,
    find_terminated_positions,
    liquidate_positions,
    portfolio_market_value,
    portfolio_total_return,
    process_expired_cf,
    trade,
)


class FlatCurve:
    """Stand-in for Curves: flat annually compounded rate, same retrieve_rates signature."""

    def __init__(self, rate: float):
        self.rate = rate

    def retrieve_rates(self, proj_step: int, target_mat: np.ndarray, type: str, spread: float) -> pd.DataFrame:
        target_mat = np.asarray(target_mat, dtype=float)
        return pd.DataFrame(data=(1 + self.rate + spread) ** (-target_mat), columns=["Discount"])


@pytest.fixture
def maturing_bond() -> CorpBond:
    # Annual 3% bond at par that pays its last coupon and notional on 1/3/2024,
    # inside the first projection year (29/4/2023 -> 29/4/2024).
    return CorpBond(
        asset_id="XS0000000007",
        nace="A1.4.5",
        issuer="Test Issuer",
        issue_date=date(2020, 3, 1),
        maturity_date=date(2024, 3, 1),
        coupon_rate=0.03,
        notional_amount=100,
        spread_country=0.0,
        spread_sector=0.0,
        zspread=0.0,
        spread_stress=0.0,
        frequency=Frequency.ANNUAL,
        recovery_rate=0.4,
        default_probability=0.0,
        units=10,
        market_price=100,
    )


def test_portfolio_total_return_adds_back_asset_income():
    assert portfolio_total_return(start_market_value=1000.0, end_market_value=980.0, asset_income=50.0) == pytest.approx(0.03)


def test_portfolio_total_return_without_income_is_price_return():
    assert portfolio_total_return(start_market_value=1000.0, end_market_value=1050.0, asset_income=0.0) == pytest.approx(0.05)


def test_portfolio_total_return_rejects_a_portfolio_with_no_assets():
    # Used to fail with a bare ZeroDivisionError
    with pytest.raises(ValueError, match="held no assets"):
        portfolio_total_return(start_market_value=0.0, end_market_value=0.0, asset_income=0.0)


@pytest.mark.parametrize(
    "market_value, cash, expected",
    [
        (0.0, -500.0, True),  # Everything sold and still short
        (0.0, 30000.0, False),  # End of the run: the assets paid out into cash
        (0.0, -5.8e-11, False),  # Rounding noise left by trade()
        (1000.0, -500.0, False),  # Assets left to sell
    ],
)
def test_assets_exhausted(market_value: float, cash: float, expected: bool):
    assert assets_exhausted(market_value, cash) is expected


def test_outflow_larger_than_the_portfolio_exhausts_the_assets():
    t0 = date(2023, 4, 29)
    eq_price = pd.DataFrame({t0: [100.0]}, index=["XXEQ00000014"])
    eq_units = pd.DataFrame({t0: [10.0]}, index=["XXEQ00000014"])
    bd_price = pd.DataFrame(columns=[t0], dtype=float)
    bd_units = pd.DataFrame(columns=[t0], dtype=float)
    bank_account = pd.DataFrame({t0: [-1500.0]})  # Owes more than the 1000 the portfolio is worth

    eq_units, bd_units, bank_account = trade(t0, bank_account, eq_units, eq_price, bd_units, bd_price)

    market_value = portfolio_market_value(eq_price, eq_units, bd_price, bd_units, t0)
    cash = float(bank_account[t0].iloc[0])
    assert market_value == pytest.approx(0.0)
    assert cash == pytest.approx(-500.0)
    assert assets_exhausted(market_value, cash)


def test_bond_maturity_is_not_reported_as_loss(maturing_bond: CorpBond):
    """
    Regression test: a bond that matures during the period drops out of the cash-flow
    matrices, reprices to zero and has its coupon and notional credited to the bank account.
    The period return must count that cash; the old price-only return reported -100%.
    """
    t0 = date(2023, 4, 29)
    t1 = date(2024, 4, 29)
    end_date = date(2033, 4, 29)

    bd_ptf = BondPortfolio({maturing_bond.asset_id: maturing_bond})
    cpn_flows = bd_ptf.create_coupon_flows(modelling_date=t0, end_date=end_date)
    not_flows = bd_ptf.create_maturity_flows(terminal_date=end_date)
    unique_cpn_dates = bd_ptf.unique_dates_profile(cpn_flows)
    unique_not_dates = bd_ptf.unique_dates_profile(not_flows)
    cpn_df = create_cashflow_dataframe(cf_dict=cpn_flows, unique_dates=unique_cpn_dates)
    not_df = create_cashflow_dataframe(cf_dict=not_flows, unique_dates=unique_not_dates)
    bd_price_df, bd_zspread_df, bd_units_df = bd_ptf.init_bond_portfolio_to_dataframe(modelling_date=t0)

    eq_price_df = pd.DataFrame(columns=[t0, t1], dtype=float)
    eq_units_df = pd.DataFrame(columns=[t0, t1], dtype=float)
    start_market_value = portfolio_market_value(eq_price_df, eq_units_df, bd_price_df, bd_units_df, t0)

    # Same order of steps as the main loop in main.py
    bd_units_df[t1] = bd_units_df[t0]
    asset_income = 0.0
    cash, cpn_df, unique_cpn_dates = process_expired_cf(unique_dates=unique_cpn_dates, expiration_date=t1, cash_flows=cpn_df, units=bd_units_df)
    asset_income += cash
    matured_bd_ids = find_terminated_positions(unique_dates=unique_not_dates, expiration_date=t1, cash_flows=not_df)
    cash, not_df, unique_not_dates = process_expired_cf(unique_dates=unique_not_dates, expiration_date=t1, cash_flows=not_df, units=bd_units_df)
    asset_income += cash

    bd_price_df[t1] = bd_price_df[t0]
    bd_price_df = bd_ptf.price_bond_portfolio(
        coupon_df=cpn_df,
        notional_df=not_df,
        proj_period=1,
        curves=FlatCurve(0.03),
        bond_zspread_df=bd_zspread_df,
        bond_price_df=bd_price_df,
        date_of_interest=t1,
    )
    end_market_value = portfolio_market_value(eq_price_df, eq_units_df, bd_price_df, bd_units_df, t1)

    # The mechanism behind the bug: no flows left, so the bond reprices to zero
    assert bd_price_df.loc["XS0000000007", t1] == pytest.approx(0.0)
    assert end_market_value == pytest.approx(0.0)
    assert end_market_value / start_market_value - 1 == pytest.approx(-1.0)

    # The coupon and notional were received as cash: 10 units x (3 + 100)
    assert asset_income == pytest.approx(1030.0)
    assert portfolio_total_return(start_market_value, end_market_value, asset_income) == pytest.approx(0.03)

    # The matured position is closed rather than left with units at a zero price
    assert matured_bd_ids == ["XS0000000007"]
    bd_units_df = liquidate_positions(units=bd_units_df, asset_ids=matured_bd_ids, current_date=t1)
    assert bd_units_df.loc["XS0000000007", t1] == 0.0
    assert bd_units_df.loc["XS0000000007", t0] == 10
