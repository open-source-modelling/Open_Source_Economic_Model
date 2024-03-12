# Main script for POC
import datetime
import logging
import os
import pandas as pd
from ConfigurationClass import Configuration
from CurvesClass import Curves
from EquityClasses import *
from BondClasses import CorpBondPortfolio
from MainLoop import *
from ImportData import get_EquityShare, get_corporate_bonds, get_settings, import_SWEiopa, get_Cash, get_Liability, \
    get_configuration
from TraceClass import tracer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(("%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])"))

file_handler = logging.FileHandler("ALM.log")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

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
    bond_portfolio_file = conf.input_bond_portfolio

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
    curves.ProjectForwardRate(settings.n_proj_years+1)
    logger.info("Calculate calibration parameter alpha")
    curves.CalibrateProjected(settings.n_proj_years+1, 0.05, 0.5, 1000)
 
    logger.info("Import cash portfolio")
    cash = get_Cash(cash_portfolio_file)
    
    logger.info("Import equities")
    equity_input_generator = get_EquityShare(equity_portfolio_file) # Create generator that contains all equity positions
    equity_input = {equity_share.asset_id: equity_share for equity_share in equity_input_generator}

    logger.info("Import corporate bonds")
    bond_input_generator = get_corporate_bonds(bond_portfolio_file)
    bond_input = {corp_bond.asset_id: corp_bond for corp_bond in bond_input_generator}

    logger.info("Create equity portfolio")
    equity_portfolio = EquitySharePortfolio(equity_input)

    logger.info("Create bond portfolio")
    bond_portfolio = CorpBondPortfolio(bond_input)
    # GENERATE ALL SYNTHETIC EQUITIES HERE
    # synt_equity_portfolio

    logger.info("Create dictionary of cash flows and dates for equities")
    dividend_dict = equity_portfolio.create_dividend_flows(settings.modelling_date, settings.end_date)
    terminal_dict = equity_portfolio.create_terminal_flows(modelling_date=settings.modelling_date,
                                                            terminal_date=settings.end_date,
                                                            terminal_rate=curves.ufr)

    logger.info("Create dictionary of cash flows and dates for corporate bonds")
    coupon_flows = bond_portfolio.create_coupon_flows(settings.modelling_date, settings.end_date)
    notional_flows = bond_portfolio.create_maturity_flows(terminal_date=settings.end_date)
    # Calculate date fractions based on modelling date
    # [all_date_frac, all_dates_considered] = equity_portfolio.create_dividend_fractions(settings.modelling_date, dividend_dates)
    # [all_dividend_date_frac, all_dividend_dates_considered] = equity_portfolio.create_terminal_fractions(settings.modelling_date, terminal_dates)

    logger.info("Find all asset cash flow dates for equities")
    unique_dividend_dates = equity_portfolio.unique_dates_profile(dividend_dict)
    unique_terminal_dates = equity_portfolio.unique_dates_profile(terminal_dict)

    logger.info("Find all asset cash flow dates for corporate bonds")
    unique_coupon_dates = bond_portfolio.unique_dates_profile(coupon_flows)
    unique_notional_dates = bond_portfolio.unique_dates_profile(notional_flows)

    logger.info("Load all liability cash flows")
    liabilities = get_Liability(liability_cashflow_file)

    logger.info("Load all liability cash flow dates")
    unique_liabilities_dates = liabilities.unique_dates_profile()

    ### -------- PREPARE INITIAL DATA FRAMES --------###
    logger.info("Initialize market dataframes")
    [equity_price_df, equity_growth_df, equity_units_df] = equity_portfolio.init_equity_portfolio_to_dataframe(settings.modelling_date)
    [bond_price_df, bond_zspread_df, bond_units_df] = bond_portfolio.init_bond_portfolio_to_dataframe(settings.modelling_date)

    bank_account = pd.DataFrame(data=[cash.bank_account], columns=[settings.modelling_date])

    # Note that it is assumed liabilities not paid at modelling date

    ### -------- PREPARE DATA STRUCTURES WITH CASH FLOWS -------- ###
    # Dataframe with equity dividend cash flows
    dividend_df = create_cashflow_dataframe(dividend_dict, unique_dividend_dates)
    
    # Dataframe with equity terminal cash flows
    terminal_df = create_cashflow_dataframe(terminal_dict, unique_terminal_dates)

    # Dataframe with bond coupon cash flows
    coupon_df = create_cashflow_dataframe(coupon_flows, unique_coupon_dates)

    # Dataframe with bond notional cash flows
    notional_df = create_cashflow_dataframe(notional_flows, unique_notional_dates)

    # DataFrame with liability cash flows
    liability_df = create_liabilities_df(liabilities)

    ### -------- PREPARE OUTPUT DATA FRAMES --------###
    previous_market_value = sum(equity_price_df[settings.modelling_date] * equity_units_df[settings.modelling_date])+ sum(bond_price_df[settings.modelling_date] * bond_units_df[settings.modelling_date])  # Value of the initial portfolio

    ini_out = {
        "Start cash": [None], 
        "End cash":[cash.bank_account], 
        "Start market value":[None], 
        "After growth market value":[None],
        "End market value":[previous_market_value], 
        "Portfolio return":[None],
        "Dividend cash flow":[None],
        "Coupon cash flow":[None],
        "Terminal cash flow":[None],
        "Notional cash flow":[None],
        "Liability cash flow":[None],
        }
    
    summary_df = pd.DataFrame(data = ini_out, index=[settings.modelling_date]) 

    # -------- GENERATE VECTOR OF NEXT PERIODS -------
    logger.info("Generate vector of future modelling periods")
    dates_of_interest = set_dates_of_interest(settings.modelling_date, settings.end_date)

    previous_date = settings.modelling_date

    logger.info("Start main loop")
    # --------- START MAIN LOOP THAT MOVES FORWARD IN TIME --------
    proj_period = 0
    for current_date in dates_of_interest.values:
        logger.info("Set last period's values as initial point for this period")
        initial_market_value = sum(equity_price_df[previous_date] * equity_units_df[previous_date]) + sum(bond_price_df[previous_date] * bond_units_df[previous_date])
        # Total value of portfolio after growth
        equity_units_df[current_date] = equity_units_df[previous_date]
        bond_units_df[current_date] = bond_units_df[previous_date]
    
        bank_account[current_date] = bank_account[previous_date]
        
        summary_df.loc[current_date, "Start cash"] = float(bank_account[previous_date])
        summary_df.loc[current_date, "Start market value"] = float(initial_market_value)

        logger.info("Calculate the fraction of time to move forward")
        time_frac = (current_date - previous_date).days / 365.5

        logger.info("Calculate expired dividends, remove them from cash flows and add to bank account")
        cash, dividend_df, unique_dividend_dates = process_expired_cf(unique_dividend_dates, current_date, dividend_df, equity_units_df)
        summary_df.loc[current_date, "Dividend cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired coupons, remove them from cash flows and add to bank account")
        cash, coupon_df, unique_coupon_dates = process_expired_cf(unique_coupon_dates, current_date, coupon_df, bond_units_df)
        summary_df.loc[current_date, "Coupon cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired terminal flows, remove them from cash flows and add to bank account")
        cash, terminal_df, unique_terminal_dates = process_expired_cf(unique_terminal_dates, current_date, terminal_df, equity_units_df)
        summary_df.loc[current_date, "Terminal cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired notional flows, remove them from cash flows and add to bank account")
        cash, notional_df, unique_notional_dates = process_expired_cf(unique_notional_dates, current_date, notional_df, bond_units_df)
        summary_df.loc[current_date, "Notional cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired liability flows, remove them from cash flows and add to bank account")
        cash, liability_df, unique_liabilities_dates = process_expired_liab(unique_liabilities_dates, current_date, liability_df)
        
        summary_df.loc[current_date, "Liability cash flow"] = -float(cash)
        bank_account[current_date] -= cash

        logger.info("Calculate market value of portfolio after stock growth")
        equity_price_df[current_date] = equity_price_df[previous_date] * (
                1 + equity_growth_df[settings.modelling_date]) ** time_frac

        logger.info("Calculate market value of fixed income portfolio in new period")
        bond_price_df[current_date] = bond_price_df[previous_date]
        
        bond_price_df = bond_portfolio.price_bond_portfolio(coupon_df, notional_df, settings, proj_period, curves, bond_zspread_df, bond_price_df, current_date)
        
        total_market_value = sum(equity_units_df[current_date]*equity_price_df[current_date])  + sum(bond_price_df[current_date] * bond_units_df[current_date]) # Total value of portfolio after growth
        
        summary_df.loc[current_date, "After growth market value"] = float(total_market_value)
        summary_df.loc[current_date, "Portfolio return"] = float(total_market_value/previous_market_value-1)

        logger.info("Trading of excess/deficit liquidity, rebalancing")

        [equity_units_df, bond_units_df, bank_account] = trade(current_date, bank_account, equity_units_df, equity_price_df, bond_units_df, bond_price_df)

        logger.info("Log final positions and prepare for entering next modelling period")
        summary_df.loc[current_date, "End cash"] = float(bank_account[current_date])
        summary_df.loc[current_date, "End market value"] = float(sum(equity_units_df[current_date]*equity_price_df[current_date])) + sum(bond_price_df[current_date] * bond_units_df[current_date])    

        previous_date = current_date
        previous_market_value = sum(equity_units_df[current_date]*equity_price_df[current_date])+ sum(bond_price_df[current_date] * bond_units_df[current_date])

        proj_period+=1

    logger.info("Main loop finished, saving results")
    summary_df.to_csv(conf.output_path+"\Results.csv")
    logger.info("Run completed")

if __name__ == "__main__":
    main()
