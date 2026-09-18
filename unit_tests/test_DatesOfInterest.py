from datetime import date

import pytest

from osem.MainLoop import set_dates_of_interest
from osem.SettingsClasses import Settings


def _settings(modelling_date: date, n_proj_years: int) -> Settings:
    return Settings(
        EIOPA_param_file="Input/Param_no_VA.csv",
        EIOPA_curves_file="Input/Curves_no_VA.csv",
        country="Slovenia",
        run_type="Risk Neutral",
        n_proj_years=n_proj_years,
        precision=1e-10,
        tau=0.0001,
        compounding=-1,
        modelling_date=modelling_date,
    )


def test_dates_are_anniversaries_ending_on_end_date():
    """
    Regression test: 365-day steps drifted a day every leap year (the 50th date fell on 16/4/2073)
    and added one period past the horizon (16/4/2074), which needed a curve that was never projected.
    """
    settings = _settings(date(2023, 4, 29), 50)
    dates = list(set_dates_of_interest(settings.modelling_date, settings.end_date))

    assert len(dates) == settings.n_proj_years
    assert dates[0] == date(2024, 4, 29)
    assert dates[-1] == settings.end_date == date(2073, 4, 29)
    assert all(d.month == 4 and d.day == 29 for d in dates)
    assert all(d <= settings.end_date for d in dates)


def test_leap_day_modelling_date():
    settings = _settings(date(2024, 2, 29), 5)
    dates = list(set_dates_of_interest(settings.modelling_date, settings.end_date))

    # Non-leap years fall back to 28 February, but leap years return to the 29th
    assert dates == [
        date(2025, 2, 28),
        date(2026, 2, 28),
        date(2027, 2, 28),
        date(2028, 2, 29),
        date(2029, 2, 28),
    ]
    assert dates[-1] == settings.end_date


@pytest.mark.parametrize("n_proj_years", [1, 2, 10])
def test_number_of_dates_equals_projection_years(n_proj_years: int):
    settings = _settings(date(2023, 4, 29), n_proj_years)
    dates = set_dates_of_interest(settings.modelling_date, settings.end_date)

    assert len(dates) == n_proj_years
    assert dates.iloc[-1] == settings.end_date
