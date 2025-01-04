import numpy as np
import pandas as pd
import datetime
import datetime as dt
from LiabilityClasses import Liability
from Agent import ollama_bigger

def create_cashflow_dataframe(cf_dict:dict, unique_dates:list) -> pd.DataFrame:
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
            cash_flows[key].loc[asset_id] = keys[key]
    return cash_flows

def calculate_expired_dates(list_of_dates: list, deadline: dt.date) -> list:
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

def set_dates_of_interest(modelling_date: dt.date, end_date: dt.date, days_interval=365) -> pd.Series:
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
    next_date_of_interest = modelling_date

    dates_of_interest = []
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

def process_expired_cf(unique_dates: list, expiration_date: dt.date, cash_flows: pd.DataFrame, units: pd.DataFrame)-> list:
    """
    Remove columns with expired dates from dataframe and sum cashflows within those columns into cash.
        
    Parameters
    ----------
    :type unique_dates: list
        The list of unoque dates at which cash flows occur
    :type expiration_date: date
        The date befor which, all cash flows are expired
    :type cash_flows: DataFrame
        The dataframe of all cashflows (per unit)
    :type units: DataFrame
        The dataframe showing the number of units of each position

        
    Returns
    -------
    :type: list
        List with the DataFrame with remaining (non-expired) cash flows, the expired cashflows summed into cash 
        and the list of remaining (non-expired) dates  
    """

    expired_dates = calculate_expired_dates(unique_dates, expiration_date)        
    cash = 0
    for expired_date in expired_dates:  # Sum expired dividend flows
        cash += sum(units[expiration_date]*cash_flows[expired_date])
        cash_flows.drop(columns=expired_date)
        unique_dates.remove(expired_date)
    return cash, cash_flows, unique_dates

def process_expired_liab(unique_dates:list, date_of_interest: dt.date, cash_flows:pd.DataFrame) -> list:
    """
    Remove columns with expired dates from dataframe and sum cashflows within those columns into cash.
    The cash flows are aggregated liabilities without any units
        
    Parameters
    ----------
    :type unique_dates: list
        The list of unoque dates at which cash flows occur
    :type expiration_date: date
        The date befor which, all cash flows are expired
    :type cash_flows: DataFrame
        The dataframe of all cashflows (per unit)
        
    Returns
    -------
    :type: list
        List with the DataFrame with remaining (non-expired) cash flow columns and the expired cashflows summed into cash  
    """

    expired_dates = calculate_expired_dates(unique_dates, date_of_interest)        
    cash = 0
    for expired_date in expired_dates:  # Sum expired dividend flows
        cash += sum(cash_flows[expired_date])
        cash_flows.drop(columns=expired_date)
        unique_dates.remove(expired_date)
    return cash, cash_flows, unique_dates

def trade(current_date: dt.date, bank_account:pd.DataFrame, eq_units:pd.DataFrame, eq_price:pd.DataFrame, bd_units:pd.DataFrame, bd_price:pd.DataFrame) -> list:
    """
    The trading algorithm that takes the price and unit number of equity positions and the bank account and
    invests/sells proportionally the assets to balance the bank account to 0.
        
    Parameters
    ----------
    :type current_date: date
        The date of the period at which the modell currently operates
    :type bank_account: DataFrame
        The dataframe with the bank_account balance at each modelling date 
    :type units: DataFrame
        The dataframe of all cashflows (per unit)
    :type units: DataFrame
        The dataframe showing the number of units of each position
                
    Returns
    -------
    :type: list
        List with the Dataframe documenting the  number of units after trading and the bank_account DataFrame with the
        updated bank account balance for the modelling date.  
    """
    
    total_market_value = sum(eq_units[current_date]*eq_price[current_date])+sum(bd_units[current_date]*bd_price[current_date])  # Total value of portfolio after growth

    response_MV = ollama_bigger(total_market_value)
    response_bank = ollama_bigger(bank_account[current_date][0])
    
#    if total_market_value <= 0:
    if response_MV["message"]["content"] == "N" or response_MV["message"]["content"] == "N.":
        pass
#    elif bank_account[current_date][0] < 0:  # Sell assets
    elif response_bank["message"]["content"] == "N" or response_bank["message"]["content"] == "N.":  # Sell assets
        percent_to_sell = min(1, -bank_account[current_date][0] / total_market_value)  # How much of the portfolio needs to be sold
        eq_units[current_date] = eq_units[current_date] * (1 - percent_to_sell) 
        bd_units[current_date] = bd_units[current_date] * (1 - percent_to_sell)

        bank_account[current_date] += total_market_value - sum(eq_units[current_date]*eq_price[current_date])-sum(bd_units[current_date]*bd_price[current_date])  # Add cash to bank account equal to shares sold
        
#    elif bank_account[current_date][0] > 0:  # Buy assets
    elif response_bank["message"]["content"] =="Y" or response_bank["message"]["content"] =="Y.":  # Buy assets
        percent_to_buy = bank_account[current_date][0] / total_market_value  # What % of the portfolio is the excess cash
        eq_units[current_date] = eq_units[current_date] * (1 + percent_to_buy)  
        bd_units[current_date] = bd_units[current_date] * (1 + percent_to_buy)  
                    
        bank_account[current_date] += total_market_value - sum(eq_units[current_date]*eq_price[current_date])-sum(bd_units[current_date]*bd_price[current_date])  # Bank account reduced for cash spent on buying shares
    else:  # Remaining cash flow is equal to 0 so no trading needed
        pass

    return [eq_units, bd_units, bank_account]