import numpy as np
import numpy.typing as npt
import pandas as pd
import datetime
import datetime as dt
import random
from typing import Dict, List, Optional, cast
from dateutil.relativedelta import relativedelta
from osem.SocietyClass import Society
from osem.LiabilityClasses import Liability
from osem.UnitLinkedClasses import PolicyExit, UnitLinkedFund, UnitLinkedPolicy

POLICY_HISTORY_COLUMNS = ["Date", "Policy_ID", "Is_Guaranteed", "Closing_MV", "Exit_Type", "Amount_Paid"]

def sum_series(values: pd.Series) -> float:
    """
    Add up the values of a Series in order. Used instead of Series.sum, which skips missing
    values, so that a missing price or cash flow still shows up as NaN in the total.

    Parameters
    ----------
    values: pd.Series
        The values to add up

    Returns
    -------
    float
        The sum of the values
    """
    return float(sum(cast(List[float], values.tolist())))

def create_cashflow_dataframe(cf_dict: dict[int, dict[datetime.date, float]], unique_dates: list[datetime.date]) -> pd.DataFrame:
    """
    Create a dataframe with dates as columns and equity shares as rows. If a cell has a non zero value, that
    means that there is a cash flow from that particular share at that time.

    Parameters
    ----------
    cf_dict: dict[int, dict[datetime.date, float]]
        Dictionary of date/cash-flow pairs for each security
    unique_dates: list[datetime.date]
        List of all relevant dates for the modelling run

    Returns
    -------
    pd.DataFrame
        Dataframe matrix with cash flows in a matrix form    
    """

    cash_flows = pd.DataFrame(data=np.zeros((len(cf_dict), len(unique_dates))),
                            columns=unique_dates, index=list(cf_dict.keys()))  # Dataframe of cashflows (columns are dates, rows, assets)

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
    list_of_dates: list[datetime.date]
        List of all the dates considered
        
    deadline: dt.date
        Last date considered

    Returns
    -------
    list[datetime.date]
        List of dates that occur before the deadline date
    """

    return list(a_date for a_date in list_of_dates if a_date <= deadline)

def set_dates_of_interest(modelling_date: dt.date, end_date: dt.date, years_interval: int = 1) -> pd.Series:
    """
    Calculates all dates at which the modelling run will run. The dates are anniversaries of the
    modelling date (MD + k years), so projection date k lines up with the projected curve for year k,
    and none falls after the end of the modelling window. When end_date is MD + n years (as
    Settings.end_date is), the last date equals end_date and there are exactly n dates.

    Parameters
    ----------
    modelling_date: dt.date
        The starting modelling date

    end_date: dt.date
        The end of the modelling window

    years_interval: int
        Number of years between two modelling dates of interest

    Returns
    -------
    pd.Series
        Series of dates at which the modell will run
    """
    dates_of_interest: list[dt.date] = []
    k = 1
    next_date_of_interest: dt.date = modelling_date + relativedelta(years=k * years_interval)
    while next_date_of_interest <= end_date:
        dates_of_interest.append(next_date_of_interest)
        k += 1
        # Always offset from the modelling date, so a 29 February start is not stuck on 28 February
        next_date_of_interest = modelling_date + relativedelta(years=k * years_interval)

    return pd.Series(dates_of_interest, name="Dates of interest")

def create_liabilities_df(liabilities: Liability) -> pd.DataFrame:
    """
    Create a liability DataFrame with dates as columns and a single row of aggregated cash flows.
    Amounts on a repeated date are added together, so each date is one column.

    Parameters
    ----------
    liabilities: Liability
        The liability with its cash flow dates and amounts

    Returns
    -------
    pd.DataFrame
        The DataFrame with liability cash flows, with liability_id as the index and the dates in
        the order they first appear in liabilities.cash_flow_dates
    """
    amounts: Dict[dt.date, float] = {}
    for cash_flow_date, amount in zip(liabilities.cash_flow_dates, liabilities.cash_flow_series):
        amounts[cash_flow_date] = amounts.get(cash_flow_date, 0.0) + amount

    cash_flows = pd.DataFrame(columns=list(amounts.keys()))
    cash_flows.loc[-1] = list(amounts.values())
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
    as_of : dt.date
        Valuation date (column name in the price and units DataFrames).

    Returns
    -------
    float
        Combined market value of equities and bonds at as_of.
    """
    return sum_series(eq_units[as_of] * eq_price[as_of]) + sum_series(bd_units[as_of] * bd_price[as_of])

def asset_class_market_value(price: pd.DataFrame, units: pd.DataFrame, as_of: dt.date) -> float:
    """
    Calculate the market value of one asset class at a given date.

    Parameters
    ----------
    price : pd.DataFrame
        Per-asset prices indexed by asset_id with date columns.
    units : pd.DataFrame
        Per-asset units indexed by asset_id with date columns.
    as_of : dt.date
        Valuation date (column name in the price and units DataFrames).

    Returns
    -------
    float
        Market value of the asset class at as_of.
    """
    return sum_series(units[as_of] * price[as_of])

def remaining_liability_payments(cash_flows: pd.DataFrame) -> float:
    """
    Add up the liability cash flows that have not expired yet, without discounting. Includes any
    payment scheduled after the end of the modelling window.

    Parameters
    ----------
    cash_flows : pd.DataFrame
        The dataframe of aggregated liability cash flows (absolute amounts, not per unit)

    Returns
    -------
    float
        Total of the remaining liability cash flows
    """
    remaining = 0.0
    for payment_date in cash_flows.columns:
        remaining += sum_series(cash_flows[payment_date])
    return remaining

def portfolio_total_return(start_market_value: float, end_market_value: float, asset_income: float) -> float:
    """
    Calculate the period total return of the invested portfolio. Cash paid out by the assets
    during the period (dividends, coupons, bond notionals) is added back to the end market value,
    because those flows are removed from the asset cash-flow matrices before repricing. Without
    them, a maturing bond would show up as a loss of its full value. Only include flows whose
    asset is no longer in end_market_value, otherwise the same value is counted twice.

    Parameters
    ----------
    start_market_value : float
        Portfolio market value at the end of the previous period.
    end_market_value : float
        Portfolio market value after growth and repricing in this period, before trading.
    asset_income : float
        Sum of asset cash flows credited to the bank account in this period. Liability and
        unit-linked policyholder flows are excluded, as they are funding flows, not performance.

    Returns
    -------
    float
        Total return of the portfolio over the period.
    """
    return float((end_market_value + asset_income) / start_market_value - 1)

def process_expired_cf(unique_dates: list[datetime.date], expiration_date: dt.date, cash_flows: pd.DataFrame, units: pd.DataFrame) -> tuple[float, pd.DataFrame, list[datetime.date]]:
    """
    Remove columns with expired dates from the cash-flow DataFrame and sum
    per-unit expired flows into cash.

    Parameters
    ----------
    unique_dates : list[datetime.date]
        Dates at which cash flows may occur (not yet expired).
    expiration_date : dt.date
        Period-end date; flows on or before this date are treated as expired.
    cash_flows : pd.DataFrame
        Per-unit cash flows (rows = asset_id, columns = dates).
    units : pd.DataFrame
        Holdings per asset_id; the expiration_date column is used for unit counts.

    Returns
    -------
    tuple[float, pd.DataFrame, list[datetime.date]]
        Expired cash total, remaining cash-flow DataFrame, and remaining dates.
    """

    expired_dates = calculate_expired_dates(list_of_dates = unique_dates, 
                                            deadline = expiration_date)
 
    cash = 0.0
    for expired_date in expired_dates:
        cash += sum_series(units[expiration_date] * cash_flows[expired_date])
    if expired_dates:
        cash_flows = cash_flows.drop(columns=expired_dates)
        unique_dates = [d for d in unique_dates if d not in expired_dates]
    return cash, cash_flows, unique_dates

def find_terminated_positions(unique_dates: list[datetime.date], expiration_date: dt.date, cash_flows: pd.DataFrame) -> list[int]:
    """
    Find the assets whose terminal cash flow expires on or before the expiration date.
    Must be called before process_expired_cf, which drops the expired columns.

    Parameters
    ----------
    unique_dates : list[datetime.date]
        Dates at which terminal cash flows may occur (not yet expired).
    expiration_date : dt.date
        Period-end date; flows on or before this date are treated as expired.
    cash_flows : pd.DataFrame
        Per-unit terminal cash flows (rows = asset_id, columns = dates).

    Returns
    -------
    list[int]
        Asset ids with a non-zero terminal cash flow in the expired window.
    """

    expired_dates = calculate_expired_dates(list_of_dates = unique_dates,
                                            deadline = expiration_date)
    if not expired_dates:
        return []
    has_terminal: npt.NDArray[np.bool_] = np.any(np.asarray(cash_flows[expired_dates], dtype=np.float64) != 0, axis=1)
    return list(cash_flows.index[has_terminal])

def liquidate_positions(units: pd.DataFrame, asset_ids: list[int], current_date: dt.date) -> pd.DataFrame:
    """
    Set the units of the given assets to zero at the current date. Used after a terminal
    cash flow has been credited to the bank account, so the position is not also kept in
    the market value (which would double count it).

    Parameters
    ----------
    units : pd.DataFrame
        Holdings per asset_id with date columns.
    asset_ids : list[int]
        Assets whose positions are sold.
    current_date : dt.date
        Modelling date column to update.

    Returns
    -------
    pd.DataFrame
        Updated units DataFrame.
    """

    if asset_ids:
        units.loc[asset_ids, current_date] = 0.0
    return units

def process_expired_liab(unique_dates: list[datetime.date], date_of_interest: dt.date, cash_flows: pd.DataFrame) -> tuple[float, pd.DataFrame, list[datetime.date]]:
    """
    Remove columns with expired dates from dataframe and sum cashflows within those columns into cash.
    The cash flows are aggregated liabilities without any units
        
    Parameters
    ----------
    unique_dates: list[datetime.date]
        The list of unique dates at which cash flows occur
    date_of_interest: dt.date
        The period-end date; cash flows on or before this date are treated as expired
    cash_flows: pd.DataFrame
        The dataframe of aggregated liability cash flows (absolute amounts, not per unit)
        
    Returns
    -------
    tuple[float, pd.DataFrame, list[datetime.date]]
        Expired cash total, remaining cash-flow DataFrame, and remaining dates.
    """

    expired_dates = calculate_expired_dates(unique_dates, date_of_interest)
    cash = 0.0
    for expired_date in expired_dates:
        cash += sum_series(cash_flows[expired_date])
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
    policies: Dict[int, UnitLinkedPolicy],
    current_date: dt.date,
    portfolio_return: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Capitalize active policy MV (and GV if guaranteed) by the period portfolio return.

    Parameters
    ----------
    mv_df: pd.DataFrame
        Market-value state matrix.
    gv_df: pd.DataFrame
        Guaranteed-value state matrix.
    policies: dict[int, UnitLinkedPolicy]
        Static policy metadata including is_guaranteed.
    current_date: date
        Current modelling date column.
    portfolio_return: float
        Period portfolio return from the asset MTM step.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Updated mv_df and gv_df.
    """
    factor = 1.0 + portfolio_return
    policy_id: int
    for policy_id in sorted(mv_df.index):
        mv_df.loc[policy_id, current_date] = float(mv_df[current_date].loc[policy_id]) * factor
        if policies[policy_id].is_guaranteed: # Only capitalize GV if the policy is guaranteed
            gv_df.loc[policy_id, current_date] = float(gv_df[current_date].loc[policy_id]) * factor
    return mv_df, gv_df


def apply_premiums(
    mv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """
    Grow premiums, allocate net to MV, and record gross premium and entry fee cash.

    Parameters
    ----------
    mv_df: pd.DataFrame
        Market-value state matrix.
    premium_df: pd.DataFrame
        Premium state matrix.
    fund: UnitLinkedFund
        Fund parameters (premium_growth, entry_fee).
    current_date: date
        Current modelling date column.
    time: float
        Elapsed year fraction for the period.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, float, float]
        Updated mv_df, premium_df, total gross premium, and total entry fee.
    """
    gross_total = 0.0
    entry_total = 0.0
    policy_id: int
    for policy_id in sorted(mv_df.index):
        prev_premium = float(premium_df[current_date].loc[policy_id])
        gross = prev_premium * ((1.0 + fund.premium_growth) ** time)
        entry = gross * fund.entry_fee
        net = gross - entry
        premium_df.loc[policy_id, current_date] = gross
        mv_df.loc[policy_id, current_date] = float(mv_df[current_date].loc[policy_id]) + net
        gross_total += gross
        entry_total += entry
    return mv_df, premium_df, gross_total, entry_total


def apply_admin_fees(
    mv_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
) -> tuple[pd.DataFrame, float]:
    """
    Deduct period-scaled admin fees from MV of active policies.

    Parameters
    ----------
    mv_df: pd.DataFrame
        Market-value state matrix.
    fund: UnitLinkedFund
        Fund parameters (admin_fee).
    current_date: date
        Current modelling date column.
    time: float
        Elapsed year fraction for the period.

    Returns
    -------
    tuple[pd.DataFrame, float]
        Updated mv_df and total admin fee cash.
    """
    fee_factor = 1.0 - ((1.0 - fund.admin_fee) ** time)
    admin_total = 0.0
    for policy_id in sorted(mv_df.index):
        mv = float(mv_df[current_date].loc[policy_id])
        fee = mv * fee_factor
        mv_df.loc[policy_id, current_date] = mv - fee
        admin_total += fee
    return mv_df, admin_total


def apply_mortality(
    mv_df: pd.DataFrame,
    gv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    policies: Dict[int, UnitLinkedPolicy],
    society: Society,
    current_date: dt.date,
    time: float,
    rng: random.Random,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, int]:
    """
    Stochastic mortality sampling: pay out full MV and remove the policy's row from every
    state matrix if drawn against period-scaled q, so it cannot be re-funded by a later
    premium/fee step or sampled again in a future period.

    Parameters
    ----------
    mv_df: pd.DataFrame
        Market-value state matrix.
    gv_df: pd.DataFrame
        Guaranteed-value state matrix.
    premium_df: pd.DataFrame
        Premium state matrix.
    policies: dict[int, UnitLinkedPolicy]
        Static policy metadata for age and sex.
    society: Society
        Mortality tables.
    current_date: date
        Current modelling date column.
    time: float
        Elapsed year fraction.
    rng: random.Random
        Seeded random number generator.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, int]
        Updated mv_df, gv_df, premium_df (dead policies removed), death benefit total, and death count.
    """
    death_total = 0.0
    death_ids: List[int] = []
    for policy_id in sorted(mv_df.index):
        policy = policies[policy_id]
        q_annual = society.mortality_rate(policy.age_at(current_date), policy.is_female)
        q_period = 1.0 - ((1.0 - q_annual) ** time)
        if rng.random() < q_period:
            death_total += float(mv_df[current_date].loc[policy_id])
            death_ids.append(policy_id)
    mv_df = mv_df.drop(index=death_ids)
    gv_df = gv_df.drop(index=death_ids)
    premium_df = premium_df.drop(index=death_ids)
    return mv_df, gv_df, premium_df, death_total, len(death_ids)


def apply_lapse(
    mv_df: pd.DataFrame,
    gv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    fund: UnitLinkedFund,
    current_date: dt.date,
    time: float,
    rng: random.Random,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, int]:
    """
    Stochastic lapse sampling on survivors: pay out full MV and remove the policy's row from
    every state matrix if drawn against period-scaled lapse, so it cannot be re-funded by a
    later premium/fee step or sampled again in a future period.

    Parameters
    ----------
    mv_df: pd.DataFrame
        Market-value state matrix.
    gv_df: pd.DataFrame
        Guaranteed-value state matrix.
    premium_df: pd.DataFrame
        Premium state matrix.
    fund: UnitLinkedFund
        Fund parameters (lapse_rate).
    current_date: date
        Current modelling date column.
    time: float
        Elapsed year fraction.
    rng: random.Random
        Seeded random number generator.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, int]
        Updated mv_df, gv_df, premium_df (lapsed policies removed), surrender total, and lapse count.
    """
    lapse_period = 1.0 - ((1.0 - fund.lapse_rate) ** time)
    surrender_total = 0.0
    lapse_ids: List[int] = []
    for policy_id in sorted(mv_df.index):
        if rng.random() < lapse_period:
            surrender_total += float(mv_df[current_date].loc[policy_id])
            lapse_ids.append(policy_id)
    mv_df = mv_df.drop(index=lapse_ids)
    gv_df = gv_df.drop(index=lapse_ids)
    premium_df = premium_df.drop(index=lapse_ids)
    return mv_df, gv_df, premium_df, surrender_total, len(lapse_ids)


def find_policy_exits(
    mv_before: pd.DataFrame,
    mv_after: pd.DataFrame,
    current_date: dt.date,
    exit_type: str,
) -> List[PolicyExit]:
    """
    Identify the policies removed by a mortality or lapse step and what each one was paid.

    Parameters
    ----------
    mv_before: pd.DataFrame
        Market-value state matrix before the step.
    mv_after: pd.DataFrame
        Market-value state matrix after the step.
    current_date: date
        Current modelling date column.
    exit_type: str
        How the policies left: "Death" or "Lapse".

    Returns
    -------
    List[PolicyExit]
        One entry per removed policy, ordered by policy_id.
    """
    exits: List[PolicyExit] = []
    policy_id: int
    for policy_id in sorted(mv_before.index):
        if policy_id not in mv_after.index:
            exits.append(PolicyExit(policy_id, exit_type, float(mv_before[current_date].loc[policy_id])))
    return exits


def record_policy_history(
    current_date: dt.date,
    mv_df: pd.DataFrame,
    exits: List[PolicyExit],
    policies: Dict[int, UnitLinkedPolicy],
) -> List[Dict[str, object]]:
    """
    Build one history row per policy that was in force during the period. A policy that exits is
    removed from mv_df, so this is the only record of its path once the run has finished.

    Parameters
    ----------
    current_date: date
        Modelling date of the rows.
    mv_df: pd.DataFrame
        Market-value state matrix after the period, holding only the policies still in force.
    exits: List[PolicyExit]
        Policies that left during the period.
    policies: dict[int, UnitLinkedPolicy]
        Static policy metadata including is_guaranteed.

    Returns
    -------
    List[Dict[str, object]]
        Rows with Date, Policy_ID, Is_Guaranteed, Closing_MV, Exit_Type and Amount_Paid.
    """
    rows: List[Dict[str, object]] = []
    policy_id: int
    for policy_id in sorted(mv_df.index):
        rows.append({
            "Date": current_date,
            "Policy_ID": policy_id,
            "Is_Guaranteed": policies[policy_id].is_guaranteed,
            "Closing_MV": float(mv_df[current_date].loc[policy_id]),
            "Exit_Type": "",
            "Amount_Paid": 0.0,
        })
    for policy_exit in exits:
        rows.append({
            "Date": current_date,
            "Policy_ID": policy_exit.policy_id,
            "Is_Guaranteed": policies[policy_exit.policy_id].is_guaranteed,
            "Closing_MV": 0.0,
            "Exit_Type": policy_exit.exit_type,
            "Amount_Paid": policy_exit.amount_paid,
        })
    return rows


def process_unit_linked_period(
    current_date: dt.date,
    previous_date: dt.date,
    portfolio_return: float,
    time: float,
    mv_df: pd.DataFrame,
    gv_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    policies: Dict[int, UnitLinkedPolicy],
    fund: UnitLinkedFund,
    society: Society,
    random_seed: int,
    proj_period: int,
    rng: Optional[random.Random] = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float], List[PolicyExit]]:
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
        Updated mv_df, gv_df, premium_df, a cashflow dict with absolute amounts, and the list of
        policies that left during the period.
    """
    mv_df[current_date] = mv_df[previous_date]
    gv_df[current_date] = gv_df[previous_date]
    premium_df[current_date] = premium_df[previous_date]

    if rng is None:
        rng = random.Random(random_seed + proj_period)

    reserve_before_return = sum_series(mv_df[current_date])
    mv_df, gv_df = capitalize_policies(
        mv_df, gv_df, policies, current_date, portfolio_return
    )
    return_credited = sum_series(mv_df[current_date]) - reserve_before_return

    mv_df, premium_df, gross_premium, entry_fee = apply_premiums(
        mv_df, premium_df, fund, current_date, time
    )
    mv_df, admin_fee = apply_admin_fees(mv_df, fund, current_date, time)

    mv_before_mortality = mv_df
    mv_df, gv_df, premium_df, death, deaths = apply_mortality(
        mv_df, gv_df, premium_df, policies, society, current_date, time, rng
    )
    exits = find_policy_exits(mv_before_mortality, mv_df, current_date, "Death")

    mv_before_lapse = mv_df
    mv_df, gv_df, premium_df, surrender, lapses = apply_lapse(
        mv_df, gv_df, premium_df, fund, current_date, time, rng
    )
    exits += find_policy_exits(mv_before_lapse, mv_df, current_date, "Lapse")

    in_force = int(mv_df.shape[0])
    cashflows: Dict[str, float] = {
        "return_credited": float(return_credited),
        "gross_premium": float(gross_premium),
        "entry_fee": float(entry_fee),
        "admin_fee": float(admin_fee),
        "death": float(death),
        "surrender": float(surrender),
        "deaths": float(deaths),
        "lapses": float(lapses),
        "in_force": float(in_force),
    }
    return mv_df, gv_df, premium_df, cashflows, exits
