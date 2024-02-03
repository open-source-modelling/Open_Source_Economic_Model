# Main script for POC
import datetime
import logging
import os
import pandas as pd

from ConfigurationClass import Configuration
from CurvesClass import Curves
from EquityClasses import *
from ExportData import save_matrices_to_csv
from ImportData import get_EquityShare, get_settings, import_SWEiopa, get_Cash, get_Liability, \
    get_configuration
from PathsClasses import Paths
from TraceClass import tracer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(("%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])"))

file_handler = logging.FileHandler("ALM.log")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

###### ALM FUNCTIONS #####
@tracer
def create_cashflow_dataframe(cash_flow_dates, unique_dates) -> pd.DataFrame:
    cash_flows = pd.DataFrame(data=np.zeros((len(cash_flow_dates), len(unique_dates))),
                              columns=unique_dates)  # Dataframe of cashflows (columns are dates, rows, assets)
    counter = 0
    for asset in cash_flow_dates:
        keys = asset.keys()
        for key in keys:
            cash_flows[key].iloc[counter] = asset[key]
        counter += 1
    return cash_flows


@tracer
def calculate_expired_dates(list_of_dates, deadline: date) -> list:
    return list(a_date for a_date in list_of_dates if a_date <= deadline)


@tracer
def set_dates_of_interest(modelling_date, end_date, days_interval=365) -> pd.Series:
    next_date_of_interest = modelling_date

    dates_of_interest = []
    while next_date_of_interest <= end_date:
        next_date_of_interest += datetime.timedelta(days=days_interval)
        dates_of_interest.append(next_date_of_interest)

    return pd.Series(dates_of_interest, name="Dates of interest")


@tracer
def create_liabilities_dataframe(liabilities) -> pd.DataFrame:
    liability_cash_flows = pd.DataFrame(columns=liabilities.cash_flow_dates)
    liability_cash_flows.loc[-1] = liabilities.cash_flow_series
    liability_cash_flows.index = [liabilities.liability_id]
    return liability_cash_flows


def get_logging_level(logging_level: str) -> int:
    if logging_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError("logging level is invalid")

    if logging_level == "DEBUG":
        return logging.DEBUG
    if logging_level == "INFO":
        return logging.INFO
    if logging_level == "WARNING":
        return logging.WARNING
    if logging_level == "ERROR":
        return logging.ERROR
    if logging_level == "CRITICAL":
        return logging.CRITICAL
    return logging.CRITICAL


def main():
    #logging.basicConfig(filename="ALM.log", level=logging.DEBUG)

    ####### PREPARATION OF ENVIRONMENT #######
    base_folder = os.getcwd()  # Get current working directory
    conf: Configuration
    conf = get_configuration(os.path.join(base_folder, "ALM.ini"), os)
    # Switches tracing on or off
    tracer.enabled = conf.trace_enabled
    # set the logging level
    logging_level: int = get_logging_level(conf.logging_level)
    # logging.basicConfig(format="blahh  %(levelname)s, (%(asctime)s): %(message)s (Line: %(lineno)d [%(filename)s])",
    #                    level=logging_level) # datefmt = "%d/%m/%Y %I:%M:%S %p"

    # logging.basicConfig(filename = conf.logging_file_name, level=logging_level, format="%(asctime)s")

    logger.setLevel = conf.logging_level
    logger.info("Configuration loaded")

    parameters_file = conf.input_parameters
    cash_portfolio_file = conf.input_cash_portfolio
    equity_portfolio_file = conf.input_equity_portfolio
    liability_cashflow_file = conf.input_liability_cashflow

    # Import run parameters
    logger.info("Importing run parameters")
    settings = get_settings(parameters_file)

    # Import risk free rate curve
    logger.info("Importing risk free rate curve")
    [maturities_country, curve_country, extra_param, Qb] = import_SWEiopa(settings.EIOPA_param_file,
                                                                          settings.EIOPA_curves_file, settings.country)
    
    # Curves object with information about term structure
    curves = Curves(extra_param["UFR"] / 100, settings.precision, settings.tau, settings.modelling_date,
                    settings.country)
    
    logger.info("Process risk free rate curve")
    curves.SetObservedTermStructure(maturity_vec=curve_country.index.tolist(), yield_vec=curve_country.values)
    
    logger.info("Calculate 1-year forward rate")
    curves.CalcFwdRates()

    logger.info("Calculate projected spot rates")
    curves.ProjectForwardRate(settings.n_proj_years)

    logger.info("Calculate calibration parameter alpha")
    curves.CalibrateProjected(settings.n_proj_years, 0.05, 0.5, 1000)
 
    #test
    #desired_mat = np.array([0.7, 1.2, 1.3543])
    #print(curves.RetrieveRates(3, desired_mat, "Discount"))
    
    logger.info("Import cash portfolio")
    cash = get_Cash(cash_portfolio_file)

    # Create generator that contains all equity positions
    logger.info("Import equities")
    equity_input_generator = get_EquityShare(equity_portfolio_file)
    equity_input = {equity_share.asset_id: equity_share for equity_share in equity_input_generator}

    # Fill portfolio with equity positions
    logger.info("Create equity portfolio")
    equity_portfolio = EquitySharePortfolio(equity_input)

    # Calculate cashflow dates based on equity information
    dividend_dates = equity_portfolio.create_dividend_dates(settings.modelling_date, settings.end_date)
    terminal_dates = equity_portfolio.create_terminal_dates(modelling_date=settings.modelling_date,
                                                            terminal_date=settings.end_date,
                                                            terminal_rate=curves.ufr)

    # Calculate date fractions based on modelling date
    # [all_date_frac, all_dates_considered] = equity_portfolio.create_dividend_fractions(settings.modelling_date, dividend_dates)
    # [all_dividend_date_frac, all_dividend_dates_considered] = equity_portfolio.create_terminal_fractions(settings.modelling_date, terminal_dates)

    unique_list = equity_portfolio.unique_dates_profile(dividend_dates)
    unique_terminal_list = equity_portfolio.unique_dates_profile(terminal_dates)

    # Load liability cashflows
    liabilities = get_Liability(liability_cashflow_file)
    unique_liabilities_list = liabilities.unique_dates_profile()

    ### -------- PREPARE INITIAL DATA FRAMES --------###
    [market_price_df, growth_rate_df] = equity_portfolio.init_equity_portfolio_to_dataframe(settings.modelling_date)

    bank_account = pd.DataFrame(data=[cash.bank_account], columns=[settings.modelling_date])

    ### -------- PREPARE OUTPUT DATA FRAMES --------###
    previous_market_value = sum(market_price_df[settings.modelling_date])  # Value of the initial portfolio

    ini_out = {
        "Start cash": [None], 
        "End cash":[cash.bank_account], 
        "Start market value":[None], 
        "After growth market value":[None],
        "End market value":[previous_market_value], 
        "Portfolio return":[None],
        "Dividend cash flow":[None],
        "Terminal cash flow":[None],
        "Liability cash flow":[None],
        }
    
    out_struct = pd.DataFrame(data = ini_out, index=[settings.modelling_date]) 
    # Note that it is assumed liabilities not paid at modelling date

    ### -------- PREPARE DATA STRUCTURES WITH CASH FLOWS -------- ###
    # Dataframe with dividend cash flows
    cash_flows = create_cashflow_dataframe(dividend_dates, unique_list)
    
    # Dataframe with terminal cash flows
    terminal_cash_flows = create_cashflow_dataframe(terminal_dates, unique_terminal_list)

    # DataFrame with liability cash flows
    liability_cash_flows = create_liabilities_dataframe(liabilities)

    # -------- GENERATE VECTOR OF NEXT PERIODS -------
    dates_of_interest = set_dates_of_interest(settings.modelling_date, settings.end_date)

    # --------- MOVE TO NEXT PERIOD --------
    previous_date_of_interest = settings.modelling_date

    for date_of_interest in dates_of_interest.values:

        # Move modelling time forward
        time_frac = (date_of_interest - previous_date_of_interest).days / 365.5

        out_struct.loc[date_of_interest, "Start cash"] = float(bank_account[previous_date_of_interest])

        bank_account[date_of_interest] = bank_account[previous_date_of_interest]

        # Which dividend dates are expired
        expired_dates = calculate_expired_dates(unique_list, date_of_interest)
        
        expired_cf = 0
        for expired_date in expired_dates:  # Sum expired dividend flows
            expired_cf += sum(cash_flows[expired_date])
            cash_flows.drop(columns=expired_date)
            unique_list.remove(expired_date)
        
        out_struct.loc[date_of_interest, "Dividend cash flow"] = float(expired_cf)
        bank_account[date_of_interest] += expired_cf

        # Which terminal dates are expired
        expired_dates = calculate_expired_dates(unique_terminal_list, date_of_interest)
        expired_cf = 0
        for expired_date in expired_dates:  # Sum expired terminal flows
            expired_cf += sum(terminal_cash_flows[expired_date])
            terminal_cash_flows.drop(columns=expired_date)
            unique_terminal_list.remove(expired_date)

        out_struct.loc[date_of_interest, "Terminal cash flow"] = float(expired_cf)
        bank_account[date_of_interest] += expired_cf

        # Which liability dates are expired
        expired_dates = calculate_expired_dates(unique_liabilities_list, date_of_interest)

        expired_cf = 0
        for expired_date in expired_dates:  # Sum expired liability flows
            expired_cf -= sum(liability_cash_flows[expired_date])
            liability_cash_flows.drop(columns=expired_date)
            unique_liabilities_list.remove(expired_date)

        out_struct.loc[date_of_interest, "Liability cash flow"] = float(expired_cf)
        bank_account[date_of_interest] += expired_cf

        # Calculate market value of portfolio after stock growth
        market_price_df[date_of_interest] = market_price_df[previous_date_of_interest] * (
                1 + growth_rate_df[settings.modelling_date]) ** time_frac

        total_market_value = sum(market_price_df[date_of_interest])  # Total value of portfolio after growth
        
        out_struct.loc[date_of_interest, "After growth market value"] = float(total_market_value)
        out_struct.loc[date_of_interest, "Portfolio return"] = float(total_market_value/previous_market_value-1)

        # Trading of assets
        if total_market_value <= 0:
            pass
        elif bank_account[date_of_interest][0] < 0:  # Sell assets
            percent_to_sell = min(1, -bank_account[date_of_interest][
                0] / total_market_value)  # How much of the portfolio needs to be sold
            market_price_df[date_of_interest] = (1 - percent_to_sell) * market_price_df[
                date_of_interest]  # Sold proportion of existing shares
            bank_account[date_of_interest] += total_market_value - sum(
                market_price_df[date_of_interest])  # Add cash to bank account equal to shares sold
            cash_flows = cash_flows.multiply(
                (1 - percent_to_sell))  # Adjust future dividend flows for new asset allocation
            terminal_cash_flows = terminal_cash_flows.multiply(
                (1 - percent_to_sell))  # Adjust terminal cash flows for new asset allocation
        elif bank_account[date_of_interest][0] > 0:  # Buy assets
            percent_to_buy = bank_account[date_of_interest][0] / total_market_value  # What % of the portfolio is the excess cash
            market_price_df[date_of_interest] = (1 + percent_to_buy) * market_price_df[
                date_of_interest]  # Bought new shares as proportion of existing shares
            bank_account[date_of_interest] += total_market_value - sum(
                market_price_df[date_of_interest])  # Bank account reduced for cash spent on buying shares
            cash_flows = cash_flows.multiply(
                1 + percent_to_buy)  # Adjust future dividend flows for new asset allocation
            terminal_cash_flows = terminal_cash_flows.multiply(
                1 + percent_to_buy)  # Adjust terminal cash flows for new asset allocation
        else:  # Remaining cash flow is equal to 0 so no trading needed
            pass

        out_struct.loc[date_of_interest, "End cash"] = float(bank_account[date_of_interest])
        out_struct.loc[date_of_interest, "End market value"] = float(sum(market_price_df[date_of_interest]))        

        previous_date_of_interest = date_of_interest
        previous_market_value = sum(market_price_df[date_of_interest])


    out_struct.to_csv("Output\Results.csv")
    # print(bank_account)
    # print(total_market_value)
    # print(sum(market_price[modelling_date_1]))
    # print(total_market_value-sum(market_price[modelling_date_1]))
    # print(cash.bank_account)


if __name__ == "__main__":
    main()
