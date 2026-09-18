import datetime
from osem.BondClasses import CorpBond
from osem.FrequencyClass import Frequency
import pytest


@pytest.fixture
def corp_bond() -> CorpBond:
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
    units = 12
    market_price = 50

    corp_bond = CorpBond(
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
        units,
        market_price)
    return corp_bond


def test_construct(corp_bond: CorpBond):
    nace = "AB.2"
    issue_date = datetime.date(2015, 12, 1)
    issuer = "Test Issuer"
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
    units = 12
    market_price = 50

    assert nace == corp_bond.nace
    assert issuer == corp_bond.issuer
    assert issue_date == corp_bond.issue_date
    assert maturity_date == corp_bond.maturity_date
    assert coupon_rate == corp_bond.coupon_rate
    assert notional_amount == corp_bond.notional_amount
    assert spread_country == corp_bond.spread_country
    assert spread_sector == corp_bond.spread_sector
    assert zspread == corp_bond.zspread
    assert spread_stress == corp_bond.spread_stress
    assert units == corp_bond.units 
    assert frequency == corp_bond.frequency
    assert recovery_rate == corp_bond.recovery_rate
    assert default_probability == corp_bond.default_probability
    assert market_price == corp_bond.market_price

def test_coupon_amount(corp_bond: CorpBond):
    # coupon_rate is the rate per payment, not annualised, so no division by the frequency
    coupon_amount = corp_bond.coupon_amount()
    coupon_amount_manual = corp_bond.notional_amount * corp_bond.coupon_rate
    assert coupon_amount == coupon_amount_manual

def test_dividend_dates(corp_bond: CorpBond):
    modelling_date = datetime.date(2023, 7, 24)
    end_date = datetime.date(2031, 12, 1)
    dividend_dates = list(corp_bond.generate_coupon_dates(modelling_date, end_date))
    assert dividend_dates[0] == datetime.date(2023, 9, 1)
    assert dividend_dates[1] == datetime.date(2023, 12, 1)
    assert dividend_dates[-1] <= corp_bond.maturity_date


def test_term_to_maturity(corp_bond: CorpBond):
    assert corp_bond.term_to_maturity(datetime.date(2029, 12, 1)) == 365
