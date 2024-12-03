# Main script for POC
import datetime
import logging
import os
import pandas as pd
from ConfigurationClass import Configuration
from CurvesClass import Curves
from EquityClasses import EquitySharePortfolio
from BondClasses import CorpBondPortfolio
from ImportData import get_configuration, get_settings, import_SWEiopa, get_Cash, get_EquityShare,get_corporate_bonds, get_Liability
from TraceClass import tracer
from MainLoop import create_cashflow_dataframe, create_liabilities_df, set_dates_of_interest, process_expired_cf, process_expired_liab, trade

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
    [maturities_country, curve_country, extra_param, Qb] =  import_SWEiopa(settings.EIOPA_param_file,
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
    eq_input = {equity_share.asset_id: equity_share for equity_share in equity_input_generator}

    logger.info("Import corporate bonds")
    bond_input_generator = get_corporate_bonds(bond_portfolio_file)
    bond_input = {corp_bond.asset_id: corp_bond for corp_bond in bond_input_generator}

    logger.info("Create equity portfolio")
    eq_ptf = EquitySharePortfolio(eq_input)

    logger.info("Create bond portfolio")
    bd_ptf = CorpBondPortfolio(bond_input)
    # GENERATE ALL SYNTHETIC EQUITIES HERE
    # synt_equity_portfolio

    logger.info("Create dictionary of cash flows and dates for equities")
    div_dict = eq_ptf.create_dividend_flows(settings.modelling_date, settings.end_date)
    ter_dict = eq_ptf.create_terminal_flows(modelling_date=settings.modelling_date,
                                                            terminal_date=settings.end_date,
                                                            terminal_rate=curves.ufr)

    logger.info("Create dictionary of cash flows and dates for corporate bonds")
    cpn_flows = bd_ptf.create_coupon_flows(settings.modelling_date, settings.end_date)
    not_flows = bd_ptf.create_maturity_flows(terminal_date=settings.end_date)

    # Calculate date fractions based on modelling date
    # [all_date_frac, all_dates_considered] = equity_portfolio.create_dividend_fractions(settings.modelling_date, dividend_dates)
    # [all_dividend_date_frac, all_dividend_dates_considered] = equity_portfolio.create_terminal_fractions(settings.modelling_date, terminal_dates)

    logger.info("Find all asset cash flow dates for equities")
    unique_div_dates = eq_ptf.unique_dates_profile(div_dict)
    unique_ter_dates = eq_ptf.unique_dates_profile(ter_dict)

    logger.info("Find all asset cash flow dates for corporate bonds")
    unique_cpn_dates = bd_ptf.unique_dates_profile(cpn_flows)
    unique_not_dates = bd_ptf.unique_dates_profile(not_flows)

    logger.info("Load all liability cash flows")
    liabilities = get_Liability(liability_cashflow_file)

    logger.info("Load all liability cash flow dates")
    unique_liabilities_dates = liabilities.unique_dates_profile()

    ### -------- PREPARE INITIAL DATA FRAMES --------###
    logger.info("Initialize market dataframes")
    [eq_price_df, eq_growth_df, eq_units_df] = eq_ptf.init_equity_portfolio_to_dataframe(settings.modelling_date)
    [bd_price_df, bd_zspread_df, bd_units_df] = bd_ptf.init_bond_portfolio_to_dataframe(settings.modelling_date)

    bank_account = pd.DataFrame(data=[cash.bank_account], columns=[settings.modelling_date])

    # Note that it is assumed liabilities not paid at modelling date

    ### -------- PREPARE DATA STRUCTURES WITH CASH FLOWS -------- ###
    # Dataframe with equity dividend cash flows
    div_df = create_cashflow_dataframe(div_dict, unique_div_dates)
    
    # Dataframe with equity terminal cash flows
    ter_df = create_cashflow_dataframe(ter_dict, unique_ter_dates)

    # Dataframe with bond coupon cash flows
    cpn_df = create_cashflow_dataframe(cpn_flows, unique_cpn_dates)

    # Dataframe with bond notional cash flows
    not_df = create_cashflow_dataframe(not_flows, unique_not_dates)

    # DataFrame with liability cash flows
    liab_df = create_liabilities_df(liabilities)

    ### -------- PREPARE OUTPUT DATA FRAMES --------###
    prev_mkt_value = sum(eq_price_df[settings.modelling_date] * eq_units_df[settings.modelling_date])+ sum(bd_price_df[settings.modelling_date] * bd_units_df[settings.modelling_date])  # Value of the initial portfolio


    ini_out = {
        "Start cash": [None], 
        "End cash":[cash.bank_account], 
        "Start market value":[None], 
        "After growth market value":[None],
        "End market value":[prev_mkt_value], 
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

    # --------- TIME 0 PREPARATIONS TO START THE MAIN LOOP --------

    proj_period = 0

    logger.info("Calibrate corporate bond z-spread")
    bd_zspread_df=bd_ptf.calibrate_bond_portfolio(bd_zspread_df, settings, proj_period, curves)

    # --------- START MAIN LOOP THAT MOVES FORWARD IN TIME --------
    logger.info("Start main loop")
    for current_date in dates_of_interest.values:
        logger.info("Set last period's values as initial point for this period")
        init_mkt_value = sum(eq_price_df[previous_date] * eq_units_df[previous_date]) + sum(bd_price_df[previous_date] * bd_units_df[previous_date])
        # Total value of portfolio after growth
        eq_units_df[current_date] = eq_units_df[previous_date]
        bd_units_df[current_date] = bd_units_df[previous_date]
    
        bank_account[current_date] = bank_account[previous_date]
        
        summary_df.loc[current_date, "Start cash"] = float(bank_account[previous_date])
        summary_df.loc[current_date, "Start market value"] = float(init_mkt_value)

        logger.info("Calculate the fraction of time to move forward")
        time_frac = (current_date - previous_date).days / 365.5

        logger.info("Calculate expired dividends, remove them from cash flows and add to bank account")
        cash, div_df, unique_div_dates = process_expired_cf(unique_div_dates, current_date, div_df, eq_units_df)
        summary_df.loc[current_date, "Dividend cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired coupons, remove them from cash flows and add to bank account")
        cash, cpn_df, unique_cpn_dates = process_expired_cf(unique_cpn_dates, current_date, cpn_df, bd_units_df)
        summary_df.loc[current_date, "Coupon cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired terminal flows, remove them from cash flows and add to bank account")
        cash, ter_df, unique_ter_dates = process_expired_cf(unique_ter_dates, current_date, ter_df, eq_units_df)
        summary_df.loc[current_date, "Terminal cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired notional flows, remove them from cash flows and add to bank account")
        cash, not_df, unique_not_dates = process_expired_cf(unique_not_dates, current_date, not_df, bd_units_df)
        summary_df.loc[current_date, "Notional cash flow"] = float(cash)
        bank_account[current_date] += cash

        logger.info("Calculate expired liability flows, remove them from cash flows and add to bank account")
        cash, liab_df, unique_liabilities_dates = process_expired_liab(unique_liabilities_dates, current_date, liab_df)
        
        summary_df.loc[current_date, "Liability cash flow"] = -float(cash)
        bank_account[current_date] -= cash

        logger.info("Calculate market value of portfolio after stock growth")
        eq_price_df[current_date] = eq_price_df[previous_date] * (
                1 + eq_growth_df[settings.modelling_date]) ** time_frac

        logger.info("Calculate market value of fixed income portfolio in new period")
        bd_price_df[current_date] = bd_price_df[previous_date]
        
        bd_price_df = bd_ptf.price_bond_portfolio(cpn_df, not_df, settings, proj_period, curves, bd_zspread_df, bd_price_df, current_date)
        
        total_market_value = sum(eq_units_df[current_date]*eq_price_df[current_date]) + sum(bd_price_df[current_date] * bd_units_df[current_date]) # Total value of portfolio after growth
        
        summary_df.loc[current_date, "After growth market value"] = float(total_market_value)
        summary_df.loc[current_date, "Portfolio return"] = float(total_market_value/prev_mkt_value-1)

        logger.info("Trading of excess/deficit liquidity, rebalancing")
        # Proportional trading without factors
        [eq_units_df, bd_units_df, bank_account] = trade(current_date, bank_account, eq_units_df, eq_price_df, bd_units_df, bd_price_df)

        logger.info("Log final positions and prepare for entering next modelling period")
        summary_df.loc[current_date, "End cash"] = float(bank_account[current_date])
        summary_df.loc[current_date, "End market value"] = float(sum(eq_units_df[current_date]*eq_price_df[current_date])) + sum(bd_price_df[current_date] * bd_units_df[current_date])    

        previous_date = current_date
        prev_mkt_value = sum(eq_units_df[current_date]*eq_price_df[current_date])+ sum(bd_price_df[current_date] * bd_units_df[current_date])

        proj_period+=1

    logger.info("Main loop finished, saving results")
    summary_df.to_csv(conf.output_path+"\Results.csv")
    logger.info("Run completed")

if __name__ == "__main__":
    main()
