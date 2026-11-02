from osem.LiabilityClasses import Liability
from osem.MainLoop import create_liabilities_df, process_expired_liab
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


@pytest.fixture
def repeated_date_liability() -> Liability:
    later_date = datetime.date(2025, 1, 1)
    earlier_date = datetime.date(2024, 1, 1)
    return Liability(liability_id=1, cash_flow_dates=[later_date, earlier_date, later_date],
                     cash_flow_series=[10.0, 20.0, 5.0])


def test_unique_dates_profile_lists_a_repeated_date_once_in_original_order(repeated_date_liability: Liability):
    assert repeated_date_liability.unique_dates_profile() == [datetime.date(2025, 1, 1), datetime.date(2024, 1, 1)]


def test_create_liabilities_df_adds_up_a_repeated_date(repeated_date_liability: Liability):
    cash_flows = create_liabilities_df(repeated_date_liability)

    assert list(cash_flows.columns) == [datetime.date(2025, 1, 1), datetime.date(2024, 1, 1)]
    assert list(cash_flows.index) == [1]
    assert cash_flows[datetime.date(2025, 1, 1)].iloc[0] == 15.0
    assert cash_flows[datetime.date(2024, 1, 1)].iloc[0] == 20.0


def test_process_expired_liab_pays_all_amounts_on_a_repeated_date(repeated_date_liability: Liability):
    """
    Two rows on the same date used to give two columns with the same name. Selecting that date
    then returned a DataFrame rather than a Series, and the run stopped with an AttributeError.
    """
    cash_flows = create_liabilities_df(repeated_date_liability)
    unique_dates = repeated_date_liability.unique_dates_profile()

    cash, cash_flows, unique_dates = process_expired_liab(unique_dates, datetime.date(2025, 1, 1), cash_flows)

    assert cash == 35.0
    assert unique_dates == []
    assert cash_flows.shape[1] == 0
