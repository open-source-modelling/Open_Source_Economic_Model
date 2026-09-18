from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from osem.BondClasses import CorpBond, CorpBondPortfolio
from osem.FrequencyClass import Frequency
from osem.MainLoop import create_cashflow_dataframe, process_expired_cf


class RecordingFlatCurve:
    """
    Stand-in for Curves with a flat annually compounded rate. Records the projection year and
    the cash-flow times it is asked for, so tests can check what the pricing code requested.
    """

    def __init__(self, rate: float):
        self.rate = rate
        self.requested_steps: list[int] = []
        self.requested_times: list[np.ndarray] = []

    def retrieve_rates(self, proj_step: int, target_mat: np.ndarray, type: str, spread: float) -> pd.DataFrame:
        target_mat = np.asarray(target_mat, dtype=float)
        self.requested_steps.append(proj_step)
        self.requested_times.append(target_mat)
        return pd.DataFrame(data=(1 + self.rate + spread) ** (-target_mat), columns=["Discount"])


T0 = date(2023, 4, 29)
T1 = date(2024, 4, 29)  # first projection date, one year after T0
END_DATE = date(2033, 4, 29)


@pytest.fixture
def par_bond() -> CorpBond:
    # Annual 3% coupon paid every 28 April until 2030; at par on a flat 3% curve with no spread.
    return CorpBond(
        asset_id=11,
        nace="A1.4.5",
        issuer="Test Issuer",
        issue_date=date(2020, 4, 28),
        maturity_date=date(2030, 4, 28),
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


def _reprice_at_first_projection_date(bond: CorpBond, curve: RecordingFlatCurve) -> pd.DataFrame:
    """Run the main-loop steps for the bond up to repricing at T1 (projection year 1)."""
    bd_ptf = CorpBondPortfolio({bond.asset_id: bond})
    cpn_flows = bd_ptf.create_coupon_flows(modelling_date=T0, end_date=END_DATE)
    not_flows = bd_ptf.create_maturity_flows(terminal_date=END_DATE)
    unique_cpn_dates = bd_ptf.unique_dates_profile(cpn_flows)
    unique_not_dates = bd_ptf.unique_dates_profile(not_flows)
    cpn_df = create_cashflow_dataframe(cf_dict=cpn_flows, unique_dates=unique_cpn_dates)
    not_df = create_cashflow_dataframe(cf_dict=not_flows, unique_dates=unique_not_dates)
    bd_price_df, bd_zspread_df, bd_units_df = bd_ptf.init_bond_portfolio_to_dataframe(modelling_date=T0)

    bd_units_df[T1] = bd_units_df[T0]
    _, cpn_df, _ = process_expired_cf(unique_dates=unique_cpn_dates, expiration_date=T1, cash_flows=cpn_df, units=bd_units_df)
    _, not_df, _ = process_expired_cf(unique_dates=unique_not_dates, expiration_date=T1, cash_flows=not_df, units=bd_units_df)

    bd_price_df[T1] = bd_price_df[T0]
    return bd_ptf.price_bond_portfolio(
        coupon_df=cpn_df,
        notional_df=not_df,
        settings=SimpleNamespace(modelling_date=T0),
        proj_period=1,
        curves=curve,
        bond_zspread_df=bd_zspread_df,
        bond_price_df=bd_price_df,
        date_of_interest=T1,
    )


def test_par_bond_stays_at_par_after_one_year(par_bond: CorpBond):
    """
    Regression test: cash flows were discounted from the modelling date instead of the
    valuation date, so a par bond lost about a year of discounting (~97.1) at every step.
    """
    bd_price_df = _reprice_at_first_projection_date(par_bond, RecordingFlatCurve(0.03))

    # Coupon dates (28 April) fall a day before the valuation anniversaries and year fractions
    # use 365.25 days, which leaves a tiny residual, hence the tolerance
    assert bd_price_df.loc[11, T1] == pytest.approx(100.0, abs=0.05)


def test_repricing_discounts_from_valuation_date(par_bond: CorpBond):
    curve = RecordingFlatCurve(0.03)
    _reprice_at_first_projection_date(par_bond, curve)

    assert curve.requested_steps == [1]
    times = curve.requested_times[0]
    # Next coupon is 28/4/2025: about one year after T1, not two years after T0
    assert times.min() == pytest.approx((date(2025, 4, 28) - T1).days / 365.25)
    # Maturity 28/4/2030 is about 6 years after T1
    assert times.max() == pytest.approx((date(2030, 4, 28) - T1).days / 365.25)


def test_price_bond_at_modelling_date_unchanged(par_bond: CorpBond):
    # At the modelling date the valuation date and modelling date coincide, so the
    # t0 z-spread calibration path (bisection_spread) prices exactly as before.
    coupons = par_bond.create_single_cash_flows(T0, END_DATE)
    notional = par_bond.create_single_maturity(END_DATE)
    curve = RecordingFlatCurve(0.03)

    price = par_bond.price_bond(coupons, notional, T0, 0, curve, 0.0)

    t = np.array([(d - T0).days / 365.25 for d in list(coupons) + list(notional)])
    cf = np.array(list(coupons.values()) + list(notional.values()))
    assert price == pytest.approx(float(np.sum(cf * 1.03 ** (-t))))
    assert curve.requested_steps == [0]
