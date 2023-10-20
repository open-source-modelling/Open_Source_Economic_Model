from LiabilityClasses import Liability
import datetime
import pytest


@pytest.fixture
def liability_position() -> Liability:
    liability_id = 1
    cash_flow_dates = [datetime.date(2015, 12, 1), datetime.date(2016, 12, 1), datetime.date(2020, 12, 1)]
    cash_flow_series = [100.0, 120.0, 150.0]

    liability_position = Liability(liability_id=liability_id, cash_flow_dates=cash_flow_dates,
                                   cash_flow_series=cash_flow_series)
    return liability_position


def test_construct():
    liability_id = 1
    cash_flow_dates = [datetime.date(2015, 12, 1), datetime.date(2016, 12, 1), datetime.date(2020, 12, 1)]
    cash_flow_series = [100.0, 120.0, 150.0]

    liability_position = Liability(liability_id=liability_id, cash_flow_dates=cash_flow_dates,
                                   cash_flow_series=cash_flow_series)

    assert liability_position.liability_id == liability_id
    assert liability_position.cash_flow_dates == cash_flow_dates
    assert liability_position.cash_flow_series == cash_flow_series
