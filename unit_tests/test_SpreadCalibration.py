"""Tests for the z-spread bisection in CorpBond.bisection_spread.

The bond price falls monotonically in the spread, so the bisection only has a root to find when
the market price lies between the prices at the two ends of the bracket. Before the bracket check
was added, an unbracketed bond walked x_start up to x_end and returned the bracket bound as if it
were a calibrated spread.
"""
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from osem.BondClasses import CorpBond
from osem.FrequencyClass import Frequency


class FlatCurve:
    """Stand-in for Curves with a flat annually compounded rate."""

    def __init__(self, rate: float):
        self.rate = rate

    def retrieve_rates(self, proj_step: int, target_mat: np.ndarray, type: str, spread: float) -> pd.DataFrame:
        target_mat = np.asarray(target_mat, dtype=float)
        return pd.DataFrame(data=(1 + self.rate + spread) ** (-target_mat), columns=["Discount"])


T0 = date(2023, 4, 29)
END_DATE = date(2033, 4, 29)
X_START, X_END = -0.2, 0.2
PRECISION = 1e-8


@pytest.fixture
def curve() -> FlatCurve:
    return FlatCurve(0.03)


@pytest.fixture
def bond() -> CorpBond:
    # Annual 3% coupon paid every 28 April until 2030, priced at par.
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


def _price(bond: CorpBond, curve: FlatCurve, spread: float) -> float:
    return bond.price_bond(
        bond.create_single_cash_flows(T0, END_DATE),
        bond.create_single_maturity(END_DATE),
        T0,
        0,
        curve,
        spread,
    )


def _calibrate(bond: CorpBond, curve: FlatCurve) -> float:
    return bond.bisection_spread(
        x_start=X_START,
        x_end=X_END,
        modelling_date=T0,
        end_date=END_DATE,
        proj_period=0,
        curves=curve,
        precision=PRECISION,
        max_iter=100000,
    )


def test_bracketed_bond_calibrates_to_its_market_price(bond: CorpBond, curve: FlatCurve):
    spread = _calibrate(bond, curve)

    assert X_START < spread < X_END
    assert _price(bond, curve, spread) == pytest.approx(bond.market_price, abs=1e-5)


def test_unbracketed_bond_raises_instead_of_returning_the_bracket_bound(bond: CorpBond, curve: FlatCurve):
    # A market price far below the price at the widest spread in the bracket: the implied spread
    # is outside [x_start, x_end], so there is no root to find.
    cheap = replace(bond, market_price=10.0)
    assert _price(cheap, curve, X_END) > cheap.market_price

    with pytest.raises(ValueError) as excinfo:
        _calibrate(cheap, curve)

    message = str(excinfo.value)
    assert "no solution" in message
    assert str(cheap.asset_id) in message


def test_root_on_the_bracket_bound_still_returns_that_bound(bond: CorpBond, curve: FlatCurve):
    # The bracket check must sit after the endpoint checks, so a bond that prices exactly at one
    # end of the bracket is calibrated rather than rejected.
    at_bound = replace(bond, market_price=_price(bond, curve, X_END))

    assert _calibrate(at_bound, curve) == X_END
