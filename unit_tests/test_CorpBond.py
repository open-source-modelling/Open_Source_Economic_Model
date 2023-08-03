import datetime
from BondClasses import Frequency, CorpBond
import pytest


@pytest.fixture
def corp_bond() -> CorpBond:
    nace = "AB.2"
    issue_date = datetime.date(2015, 12, 1)
    issuer = "Test Issuer"
    maturity_date = datetime.date(2030, 12, 1)
    coupon_rate = 0.06
    notional_amount = 100
    frequency = Frequency.QUARTERLY
    recovery_rate = 0.02
    default_probability = 0.94
    market_price = 50

    corp_bond = CorpBond(
        1,
        nace,
        issuer,
        issue_date,
        maturity_date,
        coupon_rate,
        notional_amount,
        frequency,
        recovery_rate,
        default_probability,
        market_price,
    )
    return corp_bond


def test_construct(corp_bond):
    nace = "AB.2"
    issue_date = datetime.date(2015, 12, 1)
    issuer = "Test Issuer"
    maturity_date = datetime.date(2030, 12, 1)
    coupon_rate = 0.06
    notional_amount = 100
    frequency = Frequency.QUARTERLY
    recovery_rate = 0.02
    default_probability = 0.94
    market_price = 50

    assert nace == corp_bond.nace
    assert issuer == corp_bond.issuer
    assert maturity_date == corp_bond.maturity_date
    assert coupon_rate == corp_bond.coupon_rate
    assert notional_amount == corp_bond.notional_amount
    assert frequency == corp_bond.frequency
    assert recovery_rate == corp_bond.recovery_rate
    assert default_probability == corp_bond.default_probability
    assert market_price == corp_bond.market_price


def test_dividend_amount(corp_bond):
    assert corp_bond.dividend_amount == 6


def test_dividend_dates(corp_bond):
    modelling_date = datetime.date(2023, 7, 24)
    dividend_dates = list(corp_bond.generate_coupon_dates(modelling_date))
    assert dividend_dates[0] == datetime.date(2023, 9, 1)
    assert dividend_dates[1] == datetime.date(2023, 12, 1)
    assert dividend_dates[-1] <= corp_bond.maturity_date


def test_term_to_maturity(corp_bond):
    assert corp_bond.term_to_maturity(datetime.date(2029, 12, 1)) == 365
