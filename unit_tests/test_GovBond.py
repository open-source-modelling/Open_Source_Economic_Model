"""Tests for GovBond, and for holding government and corporate bonds in one BondPortfolio."""
from dataclasses import FrozenInstanceError, replace
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from osem.BondClasses import BondPortfolio, CorpBond, FixedCouponBond, GovBond, bonds_by_asset_id
from osem.FrequencyClass import Frequency
from osem.MainLoop import create_cashflow_dataframe


class FlatCurve:
    """Stand-in for Curves with a flat annually compounded rate."""

    def __init__(self, rate: float):
        self.rate = rate

    def retrieve_rates(self, proj_step: int, target_mat: np.ndarray, type: str, spread: float) -> pd.DataFrame:
        target_mat = np.asarray(target_mat, dtype=float)
        return pd.DataFrame(data=(1 + self.rate + spread) ** (-target_mat), columns=["Discount"])


T0 = date(2023, 4, 29)
END_DATE = date(2073, 4, 29)


@pytest.fixture
def gov_bond() -> GovBond:
    # Annual 1% coupon paid every 30 June until 2030
    return GovBond(
        asset_id="5001",
        issuer_country="Slovenia",
        issue_date=date(2020, 6, 30),
        maturity_date=date(2030, 6, 30),
        coupon_rate=0.01,
        notional_amount=100,
        zspread=0.0,
        frequency=Frequency.ANNUAL,
        units=50,
        market_price=85,
    )


@pytest.fixture
def corp_bond() -> CorpBond:
    # Annual 3% coupon paid every 28 April until 2030, priced at par
    return CorpBond(
        asset_id="XS0000001234",
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


def _price(bond: FixedCouponBond, curve: FlatCurve, spread: float) -> float:
    return bond.price_bond(
        bond.create_single_cash_flows(T0, END_DATE),
        bond.create_single_maturity(END_DATE),
        T0,
        0,
        curve,
        spread,
    )


def _calibrate(bond: FixedCouponBond, curve: FlatCurve) -> float:
    return bond.bisection_spread(
        x_start=-0.2,
        x_end=0.2,
        modelling_date=T0,
        end_date=END_DATE,
        proj_period=0,
        curves=curve,
        precision=1e-8,
        max_iter=100000,
    )


def test_construct(gov_bond: GovBond):
    assert isinstance(gov_bond, FixedCouponBond)
    assert gov_bond.asset_id == "5001"
    assert gov_bond.issuer_country == "Slovenia"
    assert gov_bond.issue_date == date(2020, 6, 30)
    assert gov_bond.maturity_date == date(2030, 6, 30)
    assert gov_bond.coupon_rate == 0.01
    assert gov_bond.notional_amount == 100
    assert gov_bond.zspread == 0.0
    assert gov_bond.frequency == Frequency.ANNUAL
    assert gov_bond.units == 50
    assert gov_bond.market_price == 85


def test_is_frozen(gov_bond: GovBond):
    with pytest.raises(FrozenInstanceError):
        gov_bond.units = 10  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"asset_id": ""}, "Asset ID must be a non-empty string"),
        ({"asset_id": "   "}, "Asset ID must be a non-empty string"),
        ({"asset_id": 5001}, "Asset ID must be a non-empty string"),  # Bond ids were integers before ISINs
        ({"coupon_rate": -0.01}, "Coupon rate cannot be negative"),
        ({"coupon_rate": 1.5}, "Coupon rate cannot be greater than 1"),
        ({"units": 0}, "Units must be greater than 0"),
        ({"market_price": -1}, "Market price cannot be negative"),
        ({"frequency": 6}, "Frequency must be either"),
        ({"notional_amount": 0}, "Notional amount must be greater than 0"),
        ({"maturity_date": date(2020, 6, 30)}, "Maturity date cannot be before issue date"),
    ],
)
def test_shared_bond_checks_apply(gov_bond: GovBond, changes: dict, message: str):
    with pytest.raises(ValueError, match=message):
        replace(gov_bond, **changes)


@pytest.mark.parametrize("issuer_country", ["", "   "])
def test_rejects_empty_issuer_country(gov_bond: GovBond, issuer_country: str):
    with pytest.raises(ValueError, match="Issuer country cannot be empty"):
        replace(gov_bond, issuer_country=issuer_country)


def test_coupon_dates_and_amounts(gov_bond: GovBond):
    coupons = gov_bond.create_single_cash_flows(T0, END_DATE)

    assert list(coupons) == [date(year, 6, 30) for year in range(2023, 2031)]
    assert all(amount == pytest.approx(1.0) for amount in coupons.values())


def test_notional_repaid_at_maturity(gov_bond: GovBond):
    assert gov_bond.create_single_maturity(END_DATE) == {date(2030, 6, 30): 100}


def test_bond_alive_at_the_end_of_the_window_is_redeemed_there(gov_bond: GovBond):
    end = date(2027, 4, 29)

    assert gov_bond.create_single_maturity(end) == {end: 100}
    assert max(gov_bond.create_single_cash_flows(T0, end)) == date(2026, 6, 30)


def test_calibrates_to_its_market_price(gov_bond: GovBond):
    curve = FlatCurve(0.03)
    spread = _calibrate(gov_bond, curve)

    assert _price(gov_bond, curve, spread) == pytest.approx(gov_bond.market_price, abs=1e-5)


def test_bond_priced_above_the_risk_free_curve_gets_a_negative_spread(gov_bond: GovBond):
    # Core euro sovereigns can trade richer than the swap-based EIOPA curve
    curve = FlatCurve(0.03)
    rich = replace(gov_bond, market_price=_price(gov_bond, curve, 0.0) + 1.0)
    spread = _calibrate(rich, curve)

    assert spread < 0
    assert _price(rich, curve, spread) == pytest.approx(rich.market_price, abs=1e-5)


def test_portfolio_prices_corporate_and_government_bonds_together(gov_bond: GovBond, corp_bond: CorpBond):
    portfolio = BondPortfolio({corp_bond.asset_id: corp_bond, gov_bond.asset_id: gov_bond})
    settings = SimpleNamespace(modelling_date=T0, end_date=END_DATE)
    curve = FlatCurve(0.03)

    coupons = portfolio.create_coupon_flows(T0, END_DATE)
    notionals = portfolio.create_maturity_flows(END_DATE)
    assert set(coupons) == set(notionals) == {corp_bond.asset_id, gov_bond.asset_id}

    price_df, zspread_df, units_df = portfolio.init_bond_portfolio_to_dataframe(T0)
    assert units_df[T0].loc[gov_bond.asset_id] == gov_bond.units

    # Calibrating at t0 and repricing on the same date must give back each bond's market price
    zspread_df = portfolio.calibrate_bond_portfolio(zspread_df, settings, 0, curve)
    cpn_df = create_cashflow_dataframe(coupons, portfolio.unique_dates_profile(coupons))
    not_df = create_cashflow_dataframe(notionals, portfolio.unique_dates_profile(notionals))
    price_df = portfolio.price_bond_portfolio(cpn_df, not_df, 0, curve, zspread_df, price_df, T0)

    for bond in (corp_bond, gov_bond):
        assert price_df[T0].loc[bond.asset_id] == pytest.approx(bond.market_price, abs=1e-5)


def test_bonds_by_asset_id_keeps_both_types_in_order(gov_bond: GovBond, corp_bond: CorpBond):
    by_id = bonds_by_asset_id([corp_bond, gov_bond])

    assert list(by_id) == [corp_bond.asset_id, gov_bond.asset_id]
    assert by_id[corp_bond.asset_id] is corp_bond
    assert by_id[gov_bond.asset_id] is gov_bond


def test_asset_ids_of_selects_one_bond_type(gov_bond: GovBond, corp_bond: CorpBond):
    portfolio = BondPortfolio(bonds_by_asset_id([corp_bond, gov_bond]))

    assert portfolio.asset_ids_of(CorpBond) == [corp_bond.asset_id]
    assert portfolio.asset_ids_of(GovBond) == [gov_bond.asset_id]
    assert portfolio.asset_ids_of(FixedCouponBond) == [corp_bond.asset_id, gov_bond.asset_id]
    assert BondPortfolio().asset_ids_of(GovBond) == []


def test_bonds_by_asset_id_rejects_an_id_used_by_a_corporate_and_a_government_bond(gov_bond: GovBond, corp_bond: CorpBond):
    clash = replace(gov_bond, asset_id=corp_bond.asset_id)

    with pytest.raises(ValueError, match="Asset ID XS0000001234 is used by two bonds \\(CorpBond and GovBond\\)"):
        bonds_by_asset_id([corp_bond, clash])


def test_bonds_by_asset_id_rejects_a_repeated_id_in_one_file(corp_bond: CorpBond):
    # A dict comprehension would keep the second bond and drop the first without a warning
    with pytest.raises(ValueError, match="Asset ID XS0000001234"):
        bonds_by_asset_id([corp_bond, replace(corp_bond, units=1)])
