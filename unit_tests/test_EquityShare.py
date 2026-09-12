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
                               , spread_country=0.0
                               , spread_sector=0.0
                               , spread_stress=0.0
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
                               , spread_country=0.0
                               , spread_sector=0.0
                               , spread_stress=0.0
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


def _make_equity_share(frequency) -> EquityShare:
    return EquityShare(
        asset_id=1,
        nace="A.1.2",
        issuer="Open Source Modelling",
        issue_date=datetime.date(2015, 12, 1),
        dividend_yield=0.03,
        frequency=frequency,
        units=1,
        market_price=12.6,
        growth_rate=0.01,
        spread_country=0.0,
        spread_sector=0.0,
        spread_stress=0.0,
    )


@pytest.mark.parametrize(
    "frequency",
    [
        FrequencyClass.Frequency.ANNUAL,
        FrequencyClass.Frequency.BIANNUAL,
        FrequencyClass.Frequency.TRIANNUAL,
        FrequencyClass.Frequency.QUARTERLY,
        FrequencyClass.Frequency.MONTHLY,
        1,
        2,
        3,
        4,
        12,
    ],
)
def test_valid_frequency_accepted(frequency):
    equity_share = _make_equity_share(frequency)
    assert equity_share.frequency == frequency


@pytest.mark.parametrize("frequency", [0, -1, 5, 13, 24, 365])
def test_invalid_frequency_rejected_at_construction(frequency):
    """
    Regression test: generate_dividend_dates() computes
    relativedelta(months=(12 // self.frequency)). Any frequency > 12 makes
    12 // frequency evaluate to 0, producing a zero-length step that never
    advances the date and hangs generate_dividend_dates() (and everything
    downstream of it, such as create_single_cash_flows) in an infinite loop.
    A bad Frequency value from a data-entry error must be rejected immediately
    at construction time instead of causing a hang later on.
    """
    with pytest.raises(ValueError):
        _make_equity_share(frequency)
