import numpy as np
import pandas as pd
import datetime
import datetime as dt
from LiabilityClasses import Liability

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