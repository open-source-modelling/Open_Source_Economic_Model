import numpy as np
import pandas as pd
import datetime
import datetime as dt
import random
from typing import Dict, Optional

from LiabilityClasses import Liability, UnitLinkedFund, UnitLinkedPolicy
from SocietyClass import Society

def create_cashflow_dataframe(cf_dict: dict[int, dict[datetime.date, float]], unique_dates: list[datetime.date]) -> pd.DataFrame:
    """
    Create a dataframe with dates as columns and equity shares as rows. If a cell has a non zero value, that
    means that there is a cash flow from that particular share at that time.

    Parameters
    ----------
    :type cf_dates: pd.DataFrame
        Dictionary of date/cash-flow pairs for each security
    :type unique_dates: list
        List of all relevant dates for the modelling run

    Returns
    -------
    :type: pd.DataFrame
        Dataframe matrix with cash flows in a matrix form    
    """

    cash_flows = pd.DataFrame(data=np.zeros((len(cf_dict), len(unique_dates))),
                              columns=unique_dates, index=cf_dict.keys())  # Dataframe of cashflows (columns are dates, rows, assets)
    for asset_id in cf_dict.keys():
        keys = cf_dict[asset_id]
        for key in keys:
            cash_flows.loc[asset_id, key] = keys[key]
    return cash_flows

def calculate_expired_dates(list_of_dates: list[datetime.date], deadline: dt.date) -> list[datetime.date]:
    """
    Returns all dates before the deadline date.
    Parameters
    ----------
    :type list_of_dates: list
        List of all the dates considered
        
    :type deadline: date
        Last date considered

    Returns
    -------
    :type: list
        List of dates that occur before the deadline date
    """

    return list(a_date for a_date in list_of_dates if a_date <= deadline)

def set_dates_of_interest(modelling_date: dt.date, end_date: dt.date, days_interval: int = 365) -> pd.Series:
    """
    Calculates all dates at which the modelling run will run.

    Parameters
    ----------
    :type modelling_date: date
        The starting modelling date

    :type end_date: date
        The end of the modelling window

    :type days_interval: int
        Time difference between two modelling dates of interest

    Returns
    -------
    :type: pd.Series
        Series of dates at which the modell will run   
    """
    next_date_of_interest: dt.date = modelling_date

    dates_of_interest: list[dt.date] = []
    while next_date_of_interest <= end_date:
        next_date_of_interest += datetime.timedelta(days=days_interval)
        dates_of_interest.append(next_date_of_interest)

    return pd.Series(dates_of_interest, name="Dates of interest")

def create_liabilities_df(liabilities: Liability) -> pd.DataFrame:
    """
    Create a liability DataFrame with dates as columns and individual positions as rows.
        
    Parameters
    ----------
    :type modelling_date: date
        The starting modelling date

    Returns
    -------
    :type: pd.DataFrame
        The DataFrame with liability cash flows       
    """
    cash_flows = pd.DataFrame(columns=liabilities.cash_flow_dates)
    cash_flows.loc[-1] = liabilities.cash_flow_series
    cash_flows.index = [liabilities.liability_id]
    return cash_flows

def portfolio_market_value(
    eq_price: pd.DataFrame,
    eq_units: pd.DataFrame,
    bd_price: pd.DataFrame,
    bd_units: pd.DataFrame,
    as_of: dt.date,
) -> float:
    """
    Calculate total market value of the equity and bond portfolios at a given date.

    Parameters
    ----------
    eq_price : pd.DataFrame
        Per-asset equity prices indexed by asset_id with date columns.
    eq_units : pd.DataFrame
        Per-asset equity units indexed by asset_id with date columns.
    bd_price : pd.DataFrame
        Per-asset bond prices indexed by asset_id with date columns.
    bd_units : pd.DataFrame
        Per-asset bond units indexed by asset_id with date columns.
    as_of : date
        Valuation date (column name in the price and units DataFrames).

    Returns
    -------
    float
        Combined market value of equities and bonds at as_of.
    """
    return float(
        sum(eq_units[as_of] * eq_price[as_of])
        + sum(bd_units[as_of] * bd_price[as_of])
    )

def process_expired_cf(unique_dates: list[datetime.date], expiration_date: dt.date, cash_flows: pd.DataFrame, units: pd.DataFrame) -> tuple[float, pd.DataFrame, list[datetime.date]]:
    """
    Remove columns with expired dates from the cash-flow DataFrame and sum
    per-unit expired flows into cash.

    Parameters
    ----------
    unique_dates : list
        Dates at which cash flows may occur (not yet expired).
    expiration_date : date
        Period-end date; flows on or before this date are treated as expired.
    cash_flows : DataFrame
        Per-unit cash flows (rows = asset_id, columns = dates).
    units : DataFrame
        Holdings per asset_id; the expiration_date column is used for unit counts.

    Returns
    -------
    tuple[float, pd.DataFrame, list]
        Expired cash total, remaining cash-flow DataFrame, and remaining dates.
    """

    expired_dates = calculate_expired_dates(list_of_dates = unique_dates, 
                                            deadline = expiration_date)
 
    cash = 0.0
    for expired_date in expired_dates:
        cash += sum(units[expiration_date] * cash_flows[expired_date])
    if expired_dates:
        cash_flows = cash_flows.drop(columns=expired_dates)
        unique_dates = [d for d in unique_dates if d not in expired_dates]
    return cash, cash_flows, unique_dates

def process_expired_liab(unique_dates: list[datetime.date], date_of_interest: dt.date, cash_flows: pd.DataFrame) -> tuple[float, pd.DataFrame, list[datetime.date]]:
    """
    Remove columns with expired dates from dataframe and sum cashflows within those columns into cash.
    The cash flows are aggregated liabilities without any units
        
    Parameters
    ----------
    :type unique_dates: list
        The list of unique dates at which cash flows occur
    :type date_of_interest: date
        The period-end date; cash flows on or before this date are treated as expired
    :type cash_flows: DataFrame
        The dataframe of aggregated liability cash flows (absolute amounts, not per unit)
        
    Returns
    -------
    :type: list
        List with the DataFrame with remaining (non-expired) cash flow columns and the expired cashflows summed into cash  
    """

    expired_dates = calculate_expired_dates(unique_dates, date_of_interest)
    cash = 0.0
    for expired_date in expired_dates:
        cash += sum(cash_flows[expired_date])
    if expired_dates:
        cash_flows = cash_flows.drop(columns=expired_dates)
        unique_dates = [d for d in unique_dates if d not in expired_dates]
    return cash, cash_flows, unique_dates

def trade(current_date: dt.date, bank_account: pd.DataFrame, eq_units: pd.DataFrame, eq_price: pd.DataFrame, bd_units: pd.DataFrame, bd_price: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Proportionally buy or sell equities and bonds to drive the bank account toward zero.

    Parameters
    ----------
    current_date : date
        The modelling date for this trading step.
    bank_account : DataFrame
        Cash balance at each modelling date (single row).
    eq_units : DataFrame
        Equity units per asset_id at each modelling date.
    eq_price : DataFrame
        Equity prices per asset_id at each modelling date.
    bd_units : DataFrame
        Bond units per asset_id at each modelling date.
    bd_price : DataFrame
        Bond prices per asset_id at each modelling date.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        Updated eq_units, bd_units, and bank_account DataFrames.
    """
    
    total_market_value = portfolio_market_value(eq_price, eq_units, bd_price, bd_units, current_date)

    if total_market_value <= 0:
        pass
    elif bank_account[current_date][0] < 0:  # Sell assets
        percent_to_sell = min(1, -bank_account[current_date][0] / total_market_value)  # How much of the portfolio needs to be sold
        eq_units[current_date] = eq_units[current_date] * (1 - percent_to_sell) 
        bd_units[current_date] = bd_units[current_date] * (1 - percent_to_sell)

        bank_account[current_date] += total_market_value - portfolio_market_value(
            eq_price, eq_units, bd_price, bd_units, current_date
        )
        
    elif bank_account[current_date][0] > 0:  # Buy assets
        percent_to_buy = bank_account[current_date][0] / total_market_value  # What % of the portfolio is the excess cash
        eq_units[current_date] = eq_units[current_date] * (1 + percent_to_buy)  
        bd_units[current_date] = bd_units[current_date] * (1 + percent_to_buy)  
                    
        bank_account[current_date] += total_market_value - portfolio_market_value(
            eq_price, eq_units, bd_price, bd_units, current_date
        )
    else:  # Remaining cash flow is equal to 0 so no trading needed
        pass

    return eq_units, bd_units, bank_account


def capitalize_policies(
    mv_df: pd.DataFrame,
    gv_df: pd.DataFrame,
    active_df: pd.DataFrame,
    policies: Dict[int, UnitLinkedPolicy],
    current_date: dt.date,
    portfolio_return: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Capitalize active policy MV (and GV if guaranteed) by the period portfolio return.

    Parameters
    ----------
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type gv_df: pd.DataFrame
        Guaranteed-value state matrix.
    :type active_df: pd.DataFrame
        Active flags (1 = in force).
    :type policies: dict[int, UnitLinkedPolicy]
        Static policy metadata including is_guaranteed.
    :type current_date: date
        Current modelling date column.
    :type portfolio_return: float
        Period portfolio return from the asset MTM step.

    Returns
    -------
    :rtype: tuple[pd.DataFrame, pd.DataFrame]
        Updated mv_df and gv_df.
    """
    factor = 1.0 + portfolio_return
    for policy_id in sorted(mv_df.index):
        if active_df.loc[policy_id, current_date] <= 0:
            continue
        mv_df.loc[policy_id, current_date] = mv_df.loc[policy_id, current_date] * factor
        if policies[policy_id].is_guaranteed:
            gv_df.loc[policy_id, current_date] = gv_df.loc[policy_id, current_date] * factor
    return mv_df, gv_df


def apply_premiums(
    mv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    active_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """
    Grow premiums, allocate net to MV, and record gross premium and entry fee cash.

    Parameters
    ----------
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type premium_df: pd.DataFrame
        Premium state matrix.
    :type active_df: pd.DataFrame
        Active flags (1 = in force).
    :type fund: UnitLinkedFund
        Fund parameters (premium_growth, entry_fee).
    :type current_date: date
        Current modelling date column.
    :type time: float
        Elapsed year fraction for the period.

    Returns
    -------
    :rtype: tuple[pd.DataFrame, pd.DataFrame, float, float]
        Updated mv_df, premium_df, total gross premium, and total entry fee.
    """
    gross_total = 0.0
    entry_total = 0.0
    for policy_id in sorted(mv_df.index):
        if active_df.loc[policy_id, current_date] <= 0:
            continue
        prev_premium = float(premium_df.loc[policy_id, current_date])
        gross = prev_premium * ((1.0 + fund.premium_growth) ** time)
        entry = gross * fund.entry_fee
        net = gross - entry
        premium_df.loc[policy_id, current_date] = gross
        mv_df.loc[policy_id, current_date] = float(mv_df.loc[policy_id, current_date]) + net
        gross_total += gross
        entry_total += entry
    return mv_df, premium_df, gross_total, entry_total


def apply_admin_fees(
    mv_df: pd.DataFrame,
    active_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
) -> tuple[pd.DataFrame, float]:
    """
    Deduct period-scaled admin fees from MV of active policies.

    Parameters
    ----------
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type active_df: pd.DataFrame
        Active flags (1 = in force).
    :type fund: UnitLinkedFund
        Fund parameters (admin_fee).
    :type current_date: date
        Current modelling date column.
    :type time: float
        Elapsed year fraction for the period.

    Returns
    -------
    :rtype: tuple[pd.DataFrame, float]
        Updated mv_df and total admin fee cash.
    """
    fee_factor = 1.0 - ((1.0 - fund.admin_fee) ** time)
    admin_total = 0.0
    for policy_id in sorted(mv_df.index):
        if active_df.loc[policy_id, current_date] <= 0:
            continue
        mv = float(mv_df.loc[policy_id, current_date])
        fee = mv * fee_factor
        mv_df.loc[policy_id, current_date] = mv - fee
        admin_total += fee
    return mv_df, admin_total


def apply_mortality(
    mv_df: pd.DataFrame,
    active_df: pd.DataFrame,
    policies: Dict[int, UnitLinkedPolicy],
    society: Society,
    current_date: dt.date,
    time: float,
    rng: random.Random,
) -> tuple[pd.DataFrame, pd.DataFrame, float, int]:
    """
    Stochastic mortality sampling: liquidate full MV if drawn against period-scaled q.

    Parameters
    ----------
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type active_df: pd.DataFrame
        Active flags (1 = in force).
    :type policies: dict[int, UnitLinkedPolicy]
        Static policy metadata for age and sex.
    :type society: Society
        Mortality tables.
    :type current_date: date
        Current modelling date column.
    :type time: float
        Elapsed year fraction.
    :type rng: random.Random
        Seeded random number generator.

    Returns
    -------
    :rtype: tuple[pd.DataFrame, pd.DataFrame, float, int]
        Updated mv_df, active_df, death benefit total, and death count.
    """
    death_total = 0.0
    death_count = 0
    for policy_id in sorted(mv_df.index):
        if active_df.loc[policy_id, current_date] <= 0:
            continue
        policy = policies[policy_id]
        q_annual = society.mortality_rate(policy.age_at(current_date), policy.is_female)
        q_period = 1.0 - ((1.0 - q_annual) ** time)
        if rng.random() < q_period:
            mv = float(mv_df.loc[policy_id, current_date])
            death_total += mv
            death_count += 1
            active_df.loc[policy_id, current_date] = 0.0
            mv_df.loc[policy_id, current_date] = 0.0
    return mv_df, active_df, death_total, death_count


def apply_lapse(
    mv_df: pd.DataFrame,
    active_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
    rng: random.Random,
) -> tuple[pd.DataFrame, pd.DataFrame, float, int]:
    """
    Stochastic lapse sampling on survivors: liquidate full MV if drawn against period-scaled lapse.

    Parameters
    ----------
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type active_df: pd.DataFrame
        Active flags (1 = in force).
    :type fund: UnitLinkedFund
        Fund parameters (lapse_rate).
    :type current_date: date
        Current modelling date column.
    :type time: float
        Elapsed year fraction.
    :type rng: random.Random
        Seeded random number generator.

    Returns
    -------
    :rtype: tuple[pd.DataFrame, pd.DataFrame, float, int]
        Updated mv_df, active_df, surrender total, and lapse count.
    """
    lapse_period = 1.0 - ((1.0 - fund.lapse_rate) ** time)
    surrender_total = 0.0
    lapse_count = 0
    for policy_id in sorted(mv_df.index):
        if active_df.loc[policy_id, current_date] <= 0:
            continue
        if rng.random() < lapse_period:
            mv = float(mv_df.loc[policy_id, current_date])
            surrender_total += mv
            lapse_count += 1
            active_df.loc[policy_id, current_date] = 0.0
            mv_df.loc[policy_id, current_date] = 0.0
    return mv_df, active_df, surrender_total, lapse_count


def process_unit_linked_period(
    current_date: dt.date,
    previous_date: dt.date,
    portfolio_return: float,
    time: float,
    mv_df: pd.DataFrame,
    gv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    active_df: pd.DataFrame,
    policies: Dict[int, UnitLinkedPolicy],
    fund: UnitLinkedFund,
    society: Society,
    random_seed: int,
    proj_period: int,
    rng: Optional[random.Random] = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    Run one unit-linked period: carry forward, capitalize, premiums, fees, mortality, lapse.

    Parameters
    ----------
    :type current_date: date
        New modelling date.
    :type previous_date: date
        Previous modelling date to carry forward from.
    :type portfolio_return: float
        Period portfolio return from asset MTM.
    :type time: float
        Elapsed year fraction.
    :type mv_df: pd.DataFrame
        Market-value state matrix.
    :type gv_df: pd.DataFrame
        Guaranteed-value state matrix.
    :type premium_df: pd.DataFrame
        Premium state matrix.
    :type active_df: pd.DataFrame
        Active flags.
    :type policies: dict[int, UnitLinkedPolicy]
        Static policy metadata.
    :type fund: UnitLinkedFund
        Fund parameters.
    :type society: Society
        Mortality tables.
    :type random_seed: int
        Base seed for reproducible draws.
    :type proj_period: int
        Projection period index used with random_seed.
    :type rng: random.Random, optional
        Optional override RNG (for unit tests).

    Returns
    -------
    :rtype: tuple
        Updated mv_df, gv_df, premium_df, active_df, and a cashflow dict with absolute amounts.
    """
    mv_df[current_date] = mv_df[previous_date]
    gv_df[current_date] = gv_df[previous_date]
    premium_df[current_date] = premium_df[previous_date]
    active_df[current_date] = active_df[previous_date]

    if rng is None:
        rng = random.Random(random_seed + proj_period)

    mv_df, gv_df = capitalize_policies(
        mv_df, gv_df, active_df, policies, current_date, portfolio_return
    )
    mv_df, premium_df, gross_premium, entry_fee = apply_premiums(
        mv_df, premium_df, active_df, fund, current_date, time
    )
    mv_df, admin_fee = apply_admin_fees(mv_df, active_df, fund, current_date, time)
    mv_df, active_df, death, deaths = apply_mortality(
        mv_df, active_df, policies, society, current_date, time, rng
    )
    mv_df, active_df, surrender, lapses = apply_lapse(
        mv_df, active_df, fund, current_date, time, rng
    )

    in_force = int(active_df[current_date].sum())
    cashflows: Dict[str, float] = {
        "gross_premium": float(gross_premium),
        "entry_fee": float(entry_fee),
        "admin_fee": float(admin_fee),
        "death": float(death),
        "surrender": float(surrender),
        "deaths": float(deaths),
        "lapses": float(lapses),
        "in_force": float(in_force),
    }
    return mv_df, gv_df, premium_df, active_df, cashflows
