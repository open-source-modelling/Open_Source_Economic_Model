from BondClasses import CorpBond, CorpBondPortfolio
from FrequencyClass import Frequency
import pytest
import datetime


@pytest.fixture
def corp_bond_1() -> CorpBond:
    asset_id = 1
    nace = "AB.2"
    issuer = "Test Issuer"
    issue_date = datetime.date(2015, 12, 1)
    maturity_date = datetime.date(2030, 12, 1)
    coupon_rate = 0.06
    notional_amount = 100
    spread_country = 0.01
    spread_sector = 0.005
    zspread = 0.0012
    spread_stress = 0.0001
    frequency = Frequency.QUARTERLY
    recovery_rate = 0.02
    default_probability = 0.94
    unit = 12
    market_price = 50

    corp_bond1 = CorpBond(
        asset_id,
        nace,
        issuer,
        issue_date,
        maturity_date,
        coupon_rate,
        notional_amount,
        spread_country,
        spread_sector,
        zspread,
        spread_stress,
        frequency,
        recovery_rate,
        default_probability,
        unit,
        market_price,
    )
    return corp_bond1


@pytest.fixture()
def corp_bond_2() -> CorpBond:
    asset_id = 2
    nace = "AB.3"
    issue_date = datetime.date(2016, 7, 1)
    issuer = "Test Issuer"
    maturity_date = datetime.date(2028, 7, 1)
    coupon_rate = 0.01
    notional_amount = 100
    spread_country = 0.02
    spread_sector = 0.004
    zspread = 0.0015
    spread_stress = 0.0002
    frequency = Frequency.MONTHLY
    recovery_rate = 0.03
    default_probability = 0.93
    unit = 25
    market_price = 80

    corp_bond2 = CorpBond(
        asset_id,
        nace,
        issuer,
        issue_date,
        maturity_date,
        coupon_rate,
        notional_amount,
        spread_country,
        spread_sector,
        zspread,
        spread_stress,
        frequency,
        recovery_rate,
        default_probability,
        unit,
        market_price
    )
    return corp_bond2


def test_is_empty():
    corp_bond_portfolio = CorpBondPortfolio()
    assert corp_bond_portfolio.is_empty() is True


def test_not_is_empty(corp_bond_1: CorpBond):
    corp_bond_portfolio = CorpBondPortfolio({corp_bond_1.asset_id: corp_bond_1})
    assert corp_bond_portfolio.is_empty() is False


def test_add_to_empty_portfolio(corp_bond_1:CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    assert corporate_bond_portfolio.is_empty() is False
    assert len(corporate_bond_portfolio.corporate_bonds) == 1
    assert corporate_bond_portfolio.corporate_bonds[corp_bond_1.asset_id] == corp_bond_1
    assert (corp_bond_1.asset_id in corporate_bond_portfolio.corporate_bonds)


def test_add_to_non_empty_portfolio(corp_bond_1: CorpBond, corp_bond_2: CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    corporate_bond_portfolio.add(corp_bond_2)

    asset_id = 3
    nace = "AB.4"
    issue_date = datetime.date(2012, 2, 1)
    issuer = "Test Issuer"
    maturity_date = datetime.date(2029, 2, 1)
    coupon_rate = 0.01
    notional_amount = 100
    spread_country = 0.03
    spread_sector = 0.006
    zspread = 0.0030
    spread_stress = 0.00034
    frequency = Frequency.BIANNUAL
    recovery_rate = 0.02
    default_probability = 0.91
    unit = 5
    market_price = 90

    corp_bond3 = CorpBond(
        asset_id,
        nace,
        issuer,
        issue_date,
        maturity_date,
        coupon_rate,
        notional_amount,
        spread_country,
        spread_sector,
        zspread,
        spread_stress,
        frequency,
        recovery_rate,
        default_probability,
        unit,
        market_price)
    corporate_bond_portfolio.add(corp_bond3)
    assert len(corporate_bond_portfolio.corporate_bonds) == 3
    assert (corp_bond3.asset_id in corporate_bond_portfolio.corporate_bonds)


def test_create_coupon_dates_single_bond(corp_bond_1: CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    modelling_date = datetime.date(2015, 6, 1)
    end_date = datetime.date(2056, 6, 1)
    coupon_dates = corporate_bond_portfolio.create_aggregate_coupon_dates(modelling_date, end_date)
    coupon_amount_manual = corp_bond_1.coupon_amount()

    assert datetime.date(2023, 6, 1) in coupon_dates
    assert datetime.date(2023, 9, 1) in coupon_dates
    assert datetime.date(2023, 12, 1) in coupon_dates
    
    assert corp_bond_1.maturity_date in coupon_dates  # TODO: Check that a final coupon should be paid at maturity
    assert coupon_dates[datetime.date(2023, 6, 1)] ==  coupon_amount_manual


def test_create_coupon_dates_two_bonds(corp_bond_1: CorpBond, corp_bond_2: CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    corporate_bond_portfolio.add(corp_bond_2)
    modelling_date = datetime.date(2023, 6, 1)
    end_date = datetime.date(2023, 12, 1)
    coupon_dates = corporate_bond_portfolio.create_aggregate_coupon_dates(modelling_date, end_date)

    assert datetime.date(2023, 6, 1) in coupon_dates
    assert coupon_dates[datetime.date(2023, 6, 1)] == corp_bond_1.coupon_amount() + corp_bond_2.coupon_amount()
    assert datetime.date(2023, 7, 1) in coupon_dates


def test_create_maturity_cashflow_single_bond(corp_bond_1: CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    modelling_date = datetime.date(2023, 6, 1)
    maturity_cashflow = corporate_bond_portfolio.create_maturity_cashflow(modelling_date)
    assert len(maturity_cashflow) == 1
    assert maturity_cashflow[corp_bond_1.maturity_date] == corp_bond_1.notional_amount


def test_create_maturity_cashflow_multiple_bonds(corp_bond_1: CorpBond, corp_bond_2: CorpBond):
    corporate_bond_portfolio = CorpBondPortfolio()
    corporate_bond_portfolio.add(corp_bond_1)
    corporate_bond_portfolio.add(corp_bond_2)
    modelling_date = datetime.date(2023, 6, 1)
    maturity_cashflow = corporate_bond_portfolio.create_maturity_cashflow(modelling_date)
    assert len(maturity_cashflow) == 2
    assert corp_bond_1.maturity_date in maturity_cashflow


def test_create_maturity_cashflow_from_dict(corp_bond_1: CorpBond, corp_bond_2: CorpBond):
    corp_dict: dict
    corp_dict = {}
    corp_dict.update({corp_bond_1.asset_id: corp_bond_1})
    corp_dict.update({corp_bond_2.asset_id: corp_bond_2})
    corporate_bond_portfolio = CorpBondPortfolio(corporate_bonds=corp_dict)
    modelling_date = datetime.date(2023, 6, 1)
    maturity_cashflow = corporate_bond_portfolio.create_maturity_cashflow(modelling_date)
    assert len(maturity_cashflow) == 2
    assert corp_bond_1.maturity_date in maturity_cashflow
    assert corp_bond_2.maturity_date in maturity_cashflow
