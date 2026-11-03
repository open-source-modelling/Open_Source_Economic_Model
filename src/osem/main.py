# Main script for POC
import os
import logging
import pandas as pd
import numpy as np
from datetime import date
from typing import Dict, List, Optional
from osem.CurvesClass import Curves
from osem.SocietyClass import Society
from osem.BondClasses import BondPortfolio, CorpBond, FixedCouponBond, GovBond, bonds_by_asset_id
from osem.ConfigurationClass import Configuration
from osem.EquityClasses import EquitySharePortfolio
from osem.UnitLinkedClasses import UnitLinkedPortfolio, UnitLinkedFund, UnitLinkedPolicy
from osem.ImportData import (
    get_configuration,
    get_settings,
    import_SWEiopa,
    get_cash,
    get_equity_share,
    get_corporate_bonds,
    get_government_bonds,
    get_liability,
    get_unit_linked_policies,
    get_unit_linked_fund,
    get_society,
)
from osem.TraceClass import tracer
from osem.MainLoop import (
    create_cashflow_dataframe,
    create_liabilities_df,
    set_dates_of_interest,
    process_expired_cf,
    process_expired_liab,
    find_terminated_positions,
    liquidate_positions,
    trade,
    portfolio_market_value,
    holdings_market_value,
    remaining_liability_payments,
    portfolio_total_return,
    assets_exhausted,
    process_unit_linked_period,
    record_policy_history,
)
from osem.ReportClass import create_report
from osem.logging_utils import get_file_logger, set_log_level

# Named explicitly: run as `python -m osem.main`, __name__ is "__main__", which is outside the osem
# package logger that set_log_level reaches
logger = get_file_logger("osem.main", "ALM.log")

def get_logging_level(logging_level: str) -> int:
    """
    Convert the logging level name from ALM.ini into the matching constant of the logging module.

    Parameters
    ----------
    logging_level: str
        Name of the logging level in capitals: DEBUG, INFO, WARNING, ERROR or CRITICAL

    Returns
    -------
    int
        The matching logging module constant. Ex. logging.INFO for "INFO"

    Raises
    ------
    ValueError
        If logging_level is not one of the names above
    """
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


def main() -> None:
    """
    Run the asset-liability model from the current working directory and save the results.

    Reads ALM.ini from the current working directory and the input files it and
    Input/Parameters.csv point to. Then calibrates the risk free curve and the bond z-spreads at
    the modelling date. For each projection date, the main loop:

    1. Carries forward units and cash from the previous date
    2. Credits expired asset cash flows to the bank account, and debits expired liabilities in
       cashflow mode
    3. Grows equity prices, reprices bonds and calculates the period total return
    4. Processes the unit-linked policies in unit_linked mode
    5. Closes equity positions whose terminal value was paid out and matured bonds, then trades
       proportionally to drive the bank account toward zero

    Results are written to Results.csv in the output folder set in ALM.ini, along with
    UL_Policy_History.csv in unit_linked mode and the Report.html run report.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If there are more projection dates than projected curve years
    """
    #logging.basicConfig(filename="ALM.log", level=logging.DEBUG)

    ####### PREPARATION OF ENVIRONMENT #######
    base_folder = os.getcwd()  # Get current working directory
    conf: Configuration
    conf = get_configuration(os.path.join(base_folder, "ALM.ini"), os)
    # Switches tracing on or off
    tracer.enabled = conf.trace_enabled
    # set the logging level
    logging_level: int = get_logging_level(conf.logging_level)
    logging.basicConfig(
            format="%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])",
            level=logging_level,
        )
    set_log_level(logging_level)  # Every module's log file, and the console
    logger.info("Configuration loaded")

    parameters_file = conf.input_parameters
    cash_portfolio_file = conf.input_cash_portfolio
    equity_portfolio_file = conf.input_equity_portfolio
    liability_cashflow_file = conf.input_liability_cashflow
    corporate_bond_portfolio_file = conf.input_corporate_bond_portfolio
    government_bond_portfolio_file = conf.input_government_bond_portfolio  # Empty if ALM.ini names none

    # Import run parameters
    logger.info("Importing run parameters")
    settings = get_settings(parameters_file)
    use_unit_linked = settings.liability_mode == "unit_linked"

    # Import risk free rate curve
    logger.info("Importing risk free rate curve")
    _, curve_country, extra_param, _ = import_SWEiopa(
        param_file=settings.EIOPA_param_file,
        curves_file=settings.EIOPA_curves_file,
        country=settings.country,
    )
    
    # Curves object with information about term structure
    curves = Curves(extra_param["UFR"]/100, settings.precision, settings.tau, settings.modelling_date,
                    settings.country)
    logger.info("Process risk free rate curve")
    curves.set_observed_term_structure(
    maturity_vec=np.asarray(curve_country.index, dtype=np.float64),
    yield_vec=np.asarray(curve_country, dtype=np.float64))
 
    logger.info("Calculate 1-year forward rate")
    curves.calc_fwd_rates()
    logger.info("Calculate projected spot rates")
    curves.project_forward_rate(settings.n_proj_years+1)
    logger.info("Calculate calibration parameter alpha")
    curves.calibrate_projected(settings.n_proj_years+1, 0.05, 0.5, 1000)
 
    logger.info("Import cash portfolio")
    cash = get_cash(cash_portfolio_file)
    
    logger.info("Import equities")
    equity_input_generator = get_equity_share(equity_portfolio_file) # Create generator that contains all equity positions
    eq_input = {equity_share.asset_id: equity_share for equity_share in equity_input_generator}

    logger.info("Import corporate bonds")
    bonds: List[FixedCouponBond] = list(get_corporate_bonds(corporate_bond_portfolio_file))
    if government_bond_portfolio_file:
        logger.info("Import government bonds")
        bonds += get_government_bonds(government_bond_portfolio_file)
    # Both bond types share the bond DataFrames, so this raises if an asset id is used twice
    bond_input = bonds_by_asset_id(bonds)

    logger.info("Create equity portfolio")
    eq_ptf = EquitySharePortfolio(eq_input)

    logger.info("Create bond portfolio")
    bd_ptf = BondPortfolio(bond_input)
    # Rows of each bond type in the bond DataFrames, for the market value of each type
    corp_ids = bd_ptf.asset_ids_of(CorpBond)
    gov_ids = bd_ptf.asset_ids_of(GovBond)
    # GENERATE ALL SYNTHETIC EQUITIES HERE
    # synt_equity_portfolio

    logger.info("Create dictionary of cash flows and dates for equities")
    div_dict = eq_ptf.create_dividend_flows(modelling_date = settings.modelling_date, end_date = settings.end_date)
    ter_dict = eq_ptf.create_terminal_flows(modelling_date=settings.modelling_date,
                                                            terminal_date=settings.end_date)

    logger.info("Create dictionary of cash flows and dates for corporate and government bonds")
    cpn_flows = bd_ptf.create_coupon_flows(modelling_date=settings.modelling_date, end_date=settings.end_date)
    not_flows = bd_ptf.create_maturity_flows(terminal_date=settings.end_date)

    logger.info("Find all asset cash flow dates for equities")
    unique_div_dates = eq_ptf.unique_dates_profile(div_dict)
    unique_ter_dates = eq_ptf.unique_dates_profile(ter_dict)

    logger.info("Find all asset cash flow dates for corporate and government bonds")
    unique_cpn_dates = bd_ptf.unique_dates_profile(cpn_flows)
    unique_not_dates = bd_ptf.unique_dates_profile(not_flows)

    ul_ptf: Optional[UnitLinkedPortfolio] = None
    ul_fund: Optional[UnitLinkedFund] = None
    society: Optional[Society] = None
    ul_policies: Dict[int, UnitLinkedPolicy] = {}
    company_account = pd.DataFrame()

    ul_mv_df = ul_gv_df = ul_premium_df = pd.DataFrame([])
    unique_liabilities_dates: List[date] = []
    liab_df = pd.DataFrame()

    if use_unit_linked:
        logger.info("Load unit-linked policies, fund parameters, and mortality")
        ul_policies = {
            p.policy_id: p for p in get_unit_linked_policies(conf.input_unit_linked_policies)
        }
        ul_ptf = UnitLinkedPortfolio(ul_policies)
        ul_fund = get_unit_linked_fund(conf.input_unit_linked_fund)
        society = get_society(conf.input_mortality)
        ul_mv_df, ul_gv_df, ul_premium_df = ul_ptf.init_policy_state_to_dataframe(
            modelling_date=settings.modelling_date
        )
        company_account = pd.DataFrame(data=[0.0], columns=[settings.modelling_date])
    else:
        logger.info("Load all liability cash flows")
        liabilities = get_liability(liability_cashflow_file)
        logger.info("Load all liability cash flow dates")
        unique_liabilities_dates = liabilities.unique_dates_profile()
        liab_df = create_liabilities_df(liabilities)

    ### -------- PREPARE INITIAL DATA FRAMES --------###
    logger.info("Initialize market dataframes")
    eq_price_df, eq_growth_df, eq_units_df = eq_ptf.init_equity_portfolio_to_dataframe(
        modelling_date=settings.modelling_date
    )
    bd_price_df, bd_zspread_df, bd_units_df = bd_ptf.init_bond_portfolio_to_dataframe(
        modelling_date=settings.modelling_date
    )

    bank_account = pd.DataFrame(data=[cash.bank_account], columns=[settings.modelling_date])

    # Note that it is assumed liabilities not paid at modelling date

    ### -------- PREPARE DATA STRUCTURES WITH CASH FLOWS -------- ###
    # Dataframe with equity dividend cash flows
    div_df = create_cashflow_dataframe(cf_dict = div_dict, unique_dates = unique_div_dates)

    # Dataframe with equity terminal cash flows
    ter_df = create_cashflow_dataframe(cf_dict = ter_dict, unique_dates = unique_ter_dates)

    # Dataframe with bond coupon cash flows
    cpn_df = create_cashflow_dataframe(cf_dict = cpn_flows, unique_dates = unique_cpn_dates)

    # Dataframe with bond notional cash flows
    not_df = create_cashflow_dataframe(cf_dict = not_flows, unique_dates = unique_not_dates)

    ### -------- PREPARE OUTPUT DATA FRAMES --------###
    prev_mkt_value = portfolio_market_value(
        eq_price_df, eq_units_df, bd_price_df, bd_units_df, settings.modelling_date
    )

    ul_reserve_t0 = None
    policy_history: List[Dict[str, object]] = []
    if use_unit_linked and ul_ptf is not None:
        ul_reserve_t0 = ul_ptf.total_reserve(ul_mv_df, settings.modelling_date)
        policy_history += record_policy_history(settings.modelling_date, ul_mv_df, [], ul_policies)

    ini_out: Dict[str, List[Optional[float]]] = {
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
        "UL gross premium cash flow": [None],
        "UL entry fee cash flow": [None],
        "UL admin fee cash flow": [None],
        "UL mortality cash flow": [None],
        "UL lapse cash flow": [None],
        "UL reserve": [ul_reserve_t0],
        "Company account": [0.0 if use_unit_linked else None],
        "UL policies in force": [
            ul_mv_df[settings.modelling_date].shape[0] if use_unit_linked else 0
        ],
        "UL deaths": [None],
        "UL lapses": [None],
        "Equity market value": [holdings_market_value(eq_price_df, eq_units_df, settings.modelling_date)],
        "Bond market value": [holdings_market_value(bd_price_df, bd_units_df, settings.modelling_date)],
        "Cash before trade": [None],
        "Remaining liability payments": [
            None if use_unit_linked else remaining_liability_payments(liab_df)
        ],
        "UL return credited": [None],
        "Government bond market value": [
            holdings_market_value(bd_price_df.loc[gov_ids], bd_units_df.loc[gov_ids], settings.modelling_date)
        ],
        "Corporate bond market value": [
            holdings_market_value(bd_price_df.loc[corp_ids], bd_units_df.loc[corp_ids], settings.modelling_date)
        ],
        }
    
    summary_df = pd.DataFrame(data = ini_out, index=[settings.modelling_date]) 

    # -------- GENERATE VECTOR OF NEXT PERIODS -------
    logger.info("Generate vector of future modelling periods")
    dates_of_interest: pd.Series = set_dates_of_interest(modelling_date = settings.modelling_date, end_date = settings.end_date)
    # Projection date k is priced on the projected curve for year k; curves exist for years 0..n_proj_years
    if len(dates_of_interest) > settings.n_proj_years:
        raise ValueError(
            f"{len(dates_of_interest)} projection dates but curves are only projected for "
            f"{settings.n_proj_years} years"
        )

    previous_date: date = settings.modelling_date

    # --------- TIME 0 PREPARATIONS TO START THE MAIN LOOP --------

    proj_period = 0

    logger.info("Calibrate corporate and government bond z-spreads")
    bd_zspread_df=bd_ptf.calibrate_bond_portfolio(zspread_df=bd_zspread_df, settings=settings, proj_period=proj_period, curves=curves)

    # --------- START MAIN LOOP THAT MOVES FORWARD IN TIME --------
    logger.info("Start main loop")
    current_date: date
    for current_date in dates_of_interest.values:
        logger.info("Set last period's values as initial point for this period")
        init_mkt_value = portfolio_market_value(
            eq_price_df, eq_units_df, bd_price_df, bd_units_df, previous_date
        )
        # Total value of portfolio after growth
        eq_units_df[current_date] = eq_units_df[previous_date]
        bd_units_df[current_date] = bd_units_df[previous_date]
    
        bank_account[current_date] = bank_account[previous_date]
        if use_unit_linked:
            company_account[current_date] = company_account[previous_date]
        
        summary_df.loc[current_date, "Start cash"] = float(bank_account[previous_date].iloc[0])
        summary_df.loc[current_date, "Start market value"] = float(init_mkt_value)

        logger.info("Calculate the fraction of time to move forward")
        time_frac = (current_date - previous_date).days / 365.25

        # -------- WHICH ASSET/LIABILITY FLOWS EXIRED IN THIS PERIOD AND ADD TO BANK ACCOUNT --------
        # Asset cash flows paid out this period; added back to market value for the total return
        asset_income = 0.0

        logger.info("Calculate expired dividends, remove them from cash flows and add to bank account")
        cash, div_df, unique_div_dates = process_expired_cf(unique_dates = unique_div_dates, expiration_date = current_date, cash_flows = div_df, units = eq_units_df)
        summary_df.loc[current_date, "Dividend cash flow"] = float(cash)
        bank_account[current_date] += cash
        asset_income += cash

        logger.info("Calculate expired coupons, remove them from cash flows and add to bank account")
        cash, cpn_df, unique_cpn_dates = process_expired_cf(unique_dates = unique_cpn_dates, expiration_date = current_date, cash_flows = cpn_df, units = bd_units_df)
        summary_df.loc[current_date, "Coupon cash flow"] = float(cash)
        bank_account[current_date] += cash
        asset_income += cash

        logger.info("Calculate expired terminal flows, remove them from cash flows and add to bank account")
        terminated_eq_ids = find_terminated_positions(unique_dates = unique_ter_dates, expiration_date = current_date, cash_flows = ter_df)
        cash, ter_df, unique_ter_dates = process_expired_cf(unique_dates = unique_ter_dates, expiration_date = current_date, cash_flows = ter_df, units = eq_units_df)
        summary_df.loc[current_date, "Terminal cash flow"] = float(cash)
        bank_account[current_date] += cash
        # Not added to asset_income: these equities stay in market value until they are
        # liquidated after the return calculation, so adding the cash would count them twice.

        logger.info("Calculate expired notional flows, remove them from cash flows and add to bank account")
        matured_bd_ids = find_terminated_positions(unique_dates = unique_not_dates, expiration_date = current_date, cash_flows = not_df)
        cash, not_df, unique_not_dates = process_expired_cf(unique_dates = unique_not_dates, expiration_date = current_date, cash_flows = not_df, units = bd_units_df)
        summary_df.loc[current_date, "Notional cash flow"] = float(cash)
        bank_account[current_date] += cash
        asset_income += cash

        if not use_unit_linked:
            logger.info("Calculate expired liability flows, remove them from cash flows and add to bank account")
            cash, liab_df, unique_liabilities_dates = process_expired_liab(unique_liabilities_dates, current_date, liab_df)
            
            summary_df.loc[current_date, "Liability cash flow"] = -float(cash)
            summary_df.loc[current_date, "Remaining liability payments"] = remaining_liability_payments(liab_df)
            bank_account[current_date] -= cash

        # ------- CALCULATE GROWTH OF ASSET VALUE IN THIS PERIOD --------
        logger.info("Calculate market value of portfolio after stock growth")
        eq_price_df[current_date] = eq_price_df[previous_date] * (
                1 + eq_growth_df[settings.modelling_date]) ** time_frac

        logger.info("Calculate market value of fixed income portfolio in new period")
        bd_price_df[current_date] = bd_price_df[previous_date]
        
        # proj_period counts completed periods, so current_date is projection year proj_period + 1.
        # The projected curve for that year has maturities measured from current_date.
        bd_price_df = bd_ptf.price_bond_portfolio(coupon_df = cpn_df,
                                                  notional_df = not_df,
                                                  settings = settings,
                                                  proj_period = proj_period + 1,
                                                  curves = curves, 
                                                  bond_zspread_df = bd_zspread_df, 
                                                  bond_price_df = bd_price_df, 
                                                  date_of_interest = current_date)

        total_market_value: float = portfolio_market_value(
            eq_price_df, eq_units_df, bd_price_df, bd_units_df, current_date
        )
        
        portfolio_return: float = portfolio_total_return(
            start_market_value=prev_mkt_value,
            end_market_value=total_market_value,
            asset_income=asset_income,
        )
        summary_df.loc[current_date, "After growth market value"] = float(total_market_value)
        summary_df.loc[current_date, "Portfolio return"] = portfolio_return

        if use_unit_linked:
            assert ul_ptf is not None and ul_fund is not None and society is not None
            logger.info("Process unit-linked period (capitalize, premiums, fees, mortality, lapse)")
            ul_mv_df, ul_gv_df, ul_premium_df, ul_cfs, ul_exits = process_unit_linked_period(
                current_date=current_date,
                previous_date=previous_date,
                portfolio_return=portfolio_return,
                time=time_frac,
                mv_df=ul_mv_df,
                gv_df=ul_gv_df,
                premium_df=ul_premium_df,
                policies=ul_policies,
                fund=ul_fund,
                society=society,
                random_seed=settings.random_seed,
                proj_period=proj_period
            )
            bank_account[current_date] += ul_cfs["gross_premium"]
            bank_account[current_date] -= ul_cfs["death"] + ul_cfs["surrender"]
            company_account[current_date] += ul_cfs["entry_fee"] + ul_cfs["admin_fee"]

            policy_history += record_policy_history(current_date, ul_mv_df, ul_exits, ul_policies)

            summary_df.loc[current_date, "UL return credited"] = ul_cfs["return_credited"]
            summary_df.loc[current_date, "UL gross premium cash flow"] = ul_cfs["gross_premium"]
            summary_df.loc[current_date, "UL entry fee cash flow"] = ul_cfs["entry_fee"]
            summary_df.loc[current_date, "UL admin fee cash flow"] = ul_cfs["admin_fee"]
            summary_df.loc[current_date, "UL mortality cash flow"] = -ul_cfs["death"]
            summary_df.loc[current_date, "UL lapse cash flow"] = -ul_cfs["surrender"]
            summary_df.loc[current_date, "UL reserve"] = ul_ptf.total_reserve(
                ul_mv_df, current_date
            )
            summary_df.loc[current_date, "Company account"] = float(company_account[current_date].iloc[0])
            
            summary_df.loc[current_date, "UL policies in force"] = ul_cfs["in_force"]
            summary_df.loc[current_date, "UL deaths"] = ul_cfs["deaths"]
            summary_df.loc[current_date, "UL lapses"] = ul_cfs["lapses"]

        # Terminal value was credited to the bank account above; sell the positions so they are
        # not also counted in market value. Done after the return calculation so the period
        # return is not distorted by the sale.
        logger.info("Liquidate equity positions whose terminal value was paid out")
        eq_units_df = liquidate_positions(units = eq_units_df, asset_ids = terminated_eq_ids, current_date = current_date)

        # Matured bonds have no remaining flows and reprice to zero; close them so trade()
        # does not keep scaling units of positions that no longer exist.
        logger.info("Close bond positions whose notional was repaid")
        bd_units_df = liquidate_positions(units = bd_units_df, asset_ids = matured_bd_ids, current_date = current_date)

        logger.info("Trading of excess/deficit liquidity, rebalancing")
        summary_df.loc[current_date, "Cash before trade"] = float(bank_account[current_date].iloc[0])
        # Proportional trading without factors
        eq_units_df, bd_units_df, bank_account = trade(
            current_date=current_date,
            bank_account=bank_account,
            eq_units=eq_units_df,
            eq_price=eq_price_df,
            bd_units=bd_units_df,
            bd_price=bd_price_df,
        )


        logger.info("Log final positions and prepare for entering next modelling period")
        summary_df.loc[current_date, "End cash"] = float(bank_account[current_date].iloc[0])
        summary_df.loc[current_date, "End market value"] = portfolio_market_value(
            eq_price_df, eq_units_df, bd_price_df, bd_units_df, current_date
        )
        summary_df.loc[current_date, "Equity market value"] = holdings_market_value(eq_price_df, eq_units_df, current_date)
        summary_df.loc[current_date, "Bond market value"] = holdings_market_value(bd_price_df, bd_units_df, current_date)
        summary_df.loc[current_date, "Government bond market value"] = holdings_market_value(
            bd_price_df.loc[gov_ids], bd_units_df.loc[gov_ids], current_date
        )
        summary_df.loc[current_date, "Corporate bond market value"] = holdings_market_value(
            bd_price_df.loc[corp_ids], bd_units_df.loc[corp_ids], current_date
        )

        previous_date = current_date
        prev_mkt_value = portfolio_market_value(
            eq_price_df, eq_units_df, bd_price_df, bd_units_df, current_date
        )

        end_cash = float(bank_account[current_date].iloc[0])
        if assets_exhausted(market_value=prev_mkt_value, cash=end_cash):
            # Keep the periods run so far, so the path to the shortfall can be traced
            summary_df.to_csv(os.path.join(conf.output_path, "Results.csv"))
            logger.error(f"The assets ran out on {current_date}; Results.csv holds the periods up to then")
            raise RuntimeError(
                f"The assets ran out on {current_date}: every position was sold to pay this period's "
                f"outflows and the bank account is still {end_cash:,.2f}. The model cannot continue "
                f"without assets. Check that the assets at the modelling date cover the liabilities "
                f"(in unit_linked mode, the policies' MV). Results.csv holds the periods up to {current_date}."
            )

        proj_period+=1

    logger.info("Main loop finished, saving results")
    summary_df.to_csv(os.path.join(conf.output_path, "Results.csv"))
    if use_unit_linked:
        # Listed so that the file keeps its header even when there are no policies
        pd.DataFrame(
            policy_history,
            columns=["Date", "Policy_ID", "Is_Guaranteed", "Closing_MV", "Exit_Type", "Amount_Paid"],
        ).to_csv(os.path.join(conf.output_path, "UL_Policy_History.csv"), index=False)
    # After the csv files are saved, so a problem with the report cannot lose the results
    logger.info("Create run report")
    create_report(conf.output_path)
    logger.info("Run completed")

if __name__ == "__main__":
    main()
