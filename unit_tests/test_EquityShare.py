import datetime
from EquityClasses import EquityShare
import FrequencyClass
import pytest


@pytest.fixture
def equity_share() -> EquityShare:
    asset_id = 1
    nace = "A.1.2"
    issuer = "Open Source Modelling"
    issue_date = datetime.date(2015, 12, 1)
    dividend_yield = 0.03
    frequency = FrequencyClass.Frequency.QUARTERLY
    units= 1
    market_price = 12.6
    growth_rate = 0.01

    equity_share = EquityShare(asset_id=asset_id, nace=nace,
                               issuer=issuer
                               , issue_date=issue_date
                               , dividend_yield=dividend_yield
                               , frequency=frequency
                               , units =units
                               , market_price=market_price
                               , growth_rate=growth_rate
                               )
    return equity_share


def test_construct():
    asset_id = 1
    nace = "A.1.2"
    issuer = "Open Source Modelling"
    issue_date = datetime.date(2015, 12, 1)
    dividend_yield = 0.03
    frequency = FrequencyClass.Frequency.QUARTERLY
    units = 1
    market_price = 12.6
    growth_rate = 0.02

    test_share_1 = EquityShare(asset_id=asset_id
                               , nace=nace
                               , issuer=issuer
                               , issue_date=issue_date
                               , dividend_yield=dividend_yield
                               , frequency=frequency
                               , units = units 
                               , market_price=market_price
                               , growth_rate=growth_rate
                               )

    assert test_share_1.asset_id == asset_id
    assert test_share_1.nace == nace
    assert test_share_1.issuer == issuer
    assert test_share_1.issue_date == issue_date
    assert test_share_1.dividend_yield == dividend_yield
    assert test_share_1.frequency == frequency
    assert test_share_1.units == units
    assert test_share_1.market_price == market_price
    assert test_share_1.growth_rate == growth_rate


def test_dividend_dates(equity_share):
    modelling_date = datetime.date(2023, 7, 24)
    end_date = datetime.date(2023 + 49, 12, 31)
    dividend_dates = list(equity_share.generate_dividend_dates(modelling_date, end_date))
    assert dividend_dates[0] == datetime.date(2023, 9, 1)
    assert dividend_dates[1] == datetime.date(2023, 12, 1)
    assert dividend_dates[-1] <= end_date


def test_dividend_amount(equity_share):
    market_price = 100.0
    dividend = equity_share.dividend_amount(market_price=market_price)
    manual_calculation_dividend = market_price * 0.03
    assert dividend == manual_calculation_dividend


def test_terminal_amount_calculation(equity_share):
    """
    Capitalised market value is equal to the terminal value of a stock
    """
    growth_rate = 0.05
    terminal_rate = 0.02
    market_value = 100
    gordon_manual = market_value
    gordon_calc = equity_share.terminal_amount(market_value, growth_rate, terminal_rate)
    assert gordon_calc == gordon_manual
