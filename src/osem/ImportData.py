import os
import pandas as pd
import csv
import configparser
from typing import Any, Dict, Iterator, Optional
from datetime import date, datetime
from osem.CashClass import Cash
from osem.SocietyClass import Society
from osem.BondClasses import CorpBond, GovBond
from osem.FrequencyClass import Frequency
from osem.SettingsClasses import Settings
from osem.EquityClasses import EquityShare
from osem.LiabilityClasses import Liability
from osem.ConfigurationClass import Configuration
from osem.UnitLinkedClasses import UnitLinkedPolicy, UnitLinkedFund


def get_configuration(ini_file: str, op_sys: Any = os, config_parser: Optional[configparser.ConfigParser] = None) -> Configuration:
    """
    Read the configuration parameters of the specific run and the logging settings.

    Parameters
    ----------
    ini_file: string
    
    op_sys: Any
        Operating system module (os) or a mock object for testing purposes
    
    config_parser: Optional[configparser.ConfigParser]

    ini_file
        Relative path to the setting file

    Returns
    -------
    Configuration
        Populated Configuration class instance
    """
    configuration = Configuration()

    if config_parser is None:
        config_parser = configparser.ConfigParser()

    config_parser.read(ini_file)

    if "BASE" in config_parser:
        configuration.base_folder = config_parser["BASE"]["base_folder"]
    else:
        configuration.base_folder = op_sys.getcwd()

    if "TRACE" in config_parser:
        configuration.trace_enabled = config_parser.getboolean("TRACE", "enabled")
    else:
        configuration.trace_enabled = False

    if "LOGGING" in config_parser:
        # An older ALM.ini may still set file_name here; it is ignored, as the log file names
        # are set in code (see logging_utils.py)
        configuration.logging_level = config_parser["LOGGING"]["level"]

    if "INTERMEDIATE" in config_parser:
        intermediate = config_parser["INTERMEDIATE"]
        configuration.intermediate_enabled = config_parser.getboolean("INTERMEDIATE", "enabled")
        intermediate_path = op_sys.path.join(configuration.base_folder, intermediate["file_path"])
        configuration.intermediate_path = intermediate_path
        configuration.intermediate_cash_portfolio = op_sys.path.join(intermediate_path,
                                                                     intermediate["cash_portfolio_file"])
        configuration.intermediate_equity_portfolio_file = op_sys.path.join(intermediate_path,
                                                                            intermediate["equity_portfolio_file"])


    else:
        configuration.intermediate_enabled = False

    if "INPUT" in config_parser:
        inp = config_parser["INPUT"]
        input_path = op_sys.path.join(configuration.base_folder, inp["file_path"])
        configuration.input_path = input_path
        # An ALM.ini written before government bonds were added names the corporate file "bonds"
        corporate_bonds_key = "corporate_bonds" if "corporate_bonds" in inp else "bonds"
        configuration.input_corporate_bond_portfolio = op_sys.path.join(input_path, inp[corporate_bonds_key])
        # Optional, so that an ALM.ini written before government bonds were added still runs
        if "government_bonds" in inp:
            configuration.input_government_bond_portfolio = op_sys.path.join(
                input_path, inp["government_bonds"]
            )
        configuration.input_cash_portfolio = op_sys.path.join(input_path, inp["cash"])
        # An older ALM.ini may still name a curves file here; it is ignored, as the run reads
        # the curve file named by EIOPA_curves_file in Parameters.csv
        configuration.input_equity_portfolio = op_sys.path.join(input_path, inp["equities"])
        configuration.input_param_no_VA = op_sys.path.join(input_path, inp["param_no_VA"])
        configuration.input_spread = op_sys.path.join(input_path, inp["sector_spread"])
        configuration.input_parameters = op_sys.path.join(input_path, inp["parameters"])
        configuration.input_liability_cashflow = op_sys.path.join(input_path,
                                                                  inp["liability"])
        configuration.input_mortality = op_sys.path.join(input_path, inp["mortality"])
        if "unit_linked_policies" in inp:
            configuration.input_unit_linked_policies = op_sys.path.join(
                input_path, inp["unit_linked_policies"]
            )
        if "unit_linked_fund" in inp:
            configuration.input_unit_linked_fund = op_sys.path.join(
                input_path, inp["unit_linked_fund"]
            )

        output_path = op_sys.path.join(configuration.base_folder, inp["output_path"])
        configuration.output_path = output_path
        
    return configuration


def import_SWEiopa(param_file: str, curves_file: str, country: str) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Load the input files related to the risk free curve into an a list of liquid maturities, yields and the parameters related to the Smith&Wilson algorithm.

    Parameters
    ----------
    param_file: string
        Relative path to the risk-free-curve parameter file input file

    curves_file: string
        Relative path to the risk-free-curve shape input file

    country: string
        Country name used to filter the correct curve and parameters from other files
        
    Returns
    -------
    tuple
        Tuple with 4 Pandas dataframes. The list of liquid maturities, the yields at those maturities, the parameters and the calibration vector
    """
    
    param_raw = pd.read_csv(param_file, sep=",", index_col=0)
    maturities_country_raw = param_raw.loc[:, country + "_Maturities"].iloc[6:]
    param_country_raw = param_raw.loc[:, country + "_Values"].iloc[6:]
    extra_param = param_raw.loc[:, country + "_Values"].iloc[:6]
    relevant_positions = maturities_country_raw.notna()
    maturities_country = maturities_country_raw.loc[relevant_positions]
    Qb = param_country_raw.loc[relevant_positions]
    curve_raw = pd.read_csv(curves_file, sep=",", index_col=0)
    curve_country = curve_raw.loc[:, country]
    return maturities_country, curve_country, extra_param, Qb


def check_asset_type(row: Dict[str, str], expected: str, filename: str) -> None:
    """
    Check that a row of an asset input file holds the asset type that its loader builds, so that
    a row placed in the wrong file is reported instead of being read with the wrong columns.

    Parameters
    ----------
    row: Dict[str, str]
        One row of the input file, as read by csv.DictReader
    expected: str
        The Asset_Type value the loader accepts. Ex. expected = "Government_Bond"
    filename: str
        Path to the input file, used in the error message

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the row has no Asset_Type column or its Asset_Type is not expected
    """
    asset_type = row.get("Asset_Type")
    if asset_type is None:
        raise ValueError(f"{filename} has no Asset_Type column; every row must have Asset_Type {expected}")
    if asset_type != expected:
        raise ValueError(
            f"Asset {row.get('Asset_ID')} in {filename} has Asset_Type {asset_type}, "
            f"but this file can only hold {expected} rows"
        )


def get_corporate_bonds(filename: str) -> Iterator[CorpBond]:
    """
    Load the corporate bond input file into a CorpBond generator. Asset_ID is read as text, like
    every asset id.

    Parameters
    ----------
    filename: string
        Relative path to the corporate bond input file

    Returns
    -------
    generator
        Generator yielding one CorpBond instance per CSV row

    Raises
    ------
    ValueError
        If a row's Asset_Type is not Corporate_Bond
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            check_asset_type(row, "Corporate_Bond", filename)
            corp_bond = CorpBond(asset_id=row["Asset_ID"].strip(),
                                 nace=row["NACE"],
                                 issuer=None,
                                 issue_date=datetime.strptime(row["Issue_Date"], "%d/%m/%Y").date(),
                                 maturity_date=datetime.strptime(row["Maturity_Date"], "%d/%m/%Y").date(),
                                 coupon_rate=float(row["Coupon_Rate"]),
                                 spread_country=float(row["Spread_Country"]),
                                 spread_sector=float(row["Spread_Sector"]),
                                 zspread=float(row["Z_Spread"]),
                                 spread_stress=float(row["Spread_Stress"]),
                                 notional_amount=float(row["Notional_Amount"]),
                                 frequency=Frequency(int(row["Frequency"])),
                                 recovery_rate=float(row["Recovery_Rate"]),
                                 default_probability=float(row["Default_Probability"]),
                                 units=float(row["Units"]),
                                 market_price=float(row["Market_Price"]))
            yield corp_bond


def get_government_bonds(filename: str) -> Iterator[GovBond]:
    """
    Load the government bond input file into a GovBond generator. Asset_ID is read as text, like
    every asset id.

    Parameters
    ----------
    filename: string
        Relative path to the government bond input file

    Returns
    -------
    generator
        Generator yielding one GovBond instance per CSV row

    Raises
    ------
    ValueError
        If a row's Asset_Type is not Government_Bond
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            check_asset_type(row, "Government_Bond", filename)
            gov_bond = GovBond(asset_id=row["Asset_ID"].strip(),
                               issuer_country=row["Issuer_Country"],
                               issue_date=datetime.strptime(row["Issue_Date"], "%d/%m/%Y").date(),
                               maturity_date=datetime.strptime(row["Maturity_Date"], "%d/%m/%Y").date(),
                               coupon_rate=float(row["Coupon_Rate"]),
                               notional_amount=float(row["Notional_Amount"]),
                               zspread=float(row["Z_Spread"]),
                               frequency=Frequency(int(row["Frequency"])),
                               units=float(row["Units"]),
                               market_price=float(row["Market_Price"]))
            yield gov_bond


def get_equity_share(filename: str) -> Iterator[EquityShare]:
    """
    Load an equity input file into an EquityShare class generator. Asset_ID is read as text, like
    every asset id.

    Parameters
    ----------
    filename: string
        Relative path to the equity input file

    Returns
    -------
    generator
        Generator returning a filled EquityShare class of a single position
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            equity_share = EquityShare(asset_id=row["Asset_ID"].strip(),
                                       nace=row["NACE"],
                                       issuer=None,
                                       issue_date=datetime.strptime(row["Issue_Date"], "%d/%m/%Y").date(),
                                       dividend_yield=float(row["Dividend_Yield"]),
                                       frequency=Frequency(int(row["Frequency"])),
                                       units = float(row["Units"]),
                                       market_price=float(row["Market_Price"]),
                                       growth_rate=float(row["Growth_Rate"]),
                                       spread_country=float(row["Spread_Country"]),
                                       spread_sector=float(row["Spread_Sector"]),
                                       spread_stress=float(row["Spread_Stress"]))
            yield equity_share


def get_cash(filename: str) -> Cash:
    """
    Load the initial cash input file into a Cash class object. Asset_ID is read as text, like
    every asset id.

    Parameters
    ----------
    filename: string
        Relative path to the cash input file

    Returns
    -------
    Cash
        Returning a filled Cash class with the initial cash position
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        cash: Optional[Cash] = None
        for row in reader:
            cash = Cash(asset_id=row["Asset_ID"].strip(),
                        bank_account=float(row["Bank_Account"]))
        if cash is None:
            raise ValueError(f"No cash row found in {filename}")
        return cash
        

def get_liability(filename: str) -> Liability:
    """
    Load the liability cash-flow input file into a Liability object.

    Parameters
    ----------
    filename: string
        Relative path to the liability cash flows input file

    Returns
    -------
    Liability
        A Liability instance with cash flow dates and amounts from the CSV

    """
    liability_id = 1  # To Remove and abstract away
    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        cash_flow_series: list[float] = []
        cash_flow_date: list[date] = []
        for row in reader:
            cash_flow_date.append(datetime.strptime(row["Liability_Date"], '%d/%m/%Y').date())
            cash_flow_series.append(float(row["Liability_Size"]))
        liabilities = Liability(liability_id=liability_id, cash_flow_dates=cash_flow_date,
                                cash_flow_series=cash_flow_series)
        return liabilities


def get_settings(filename: str) -> Settings:
    """
    Load the settings files into a Settings class object.

    Parameters
    ----------
    filename: string
        Relative path to the settings input file

    Returns
    -------
    Settings
        A populated Settings class

    """
    with open(filename, mode="r", encoding="utf-8-sig") as csvfile:
        read_dict: dict[str, str] = {}
        reader = csv.DictReader(csvfile)
        for row in reader:
            read_dict[row["Parameter"]] = row["Value"]

        # Rows not read below are ignored, so an older Parameters.csv that still has run_type or
        # compounding rows loads; neither was used, and both have been removed
        setting = Settings(EIOPA_param_file=read_dict["EIOPA_param_file"],
                           EIOPA_curves_file=read_dict["EIOPA_curves_file"],
                           country=read_dict["country"],
                           n_proj_years=int(read_dict["n_proj_years"]),
                           precision=float(read_dict["Precision"]),
                           tau=float(read_dict["Tau"]),
                           modelling_date=datetime.strptime(read_dict["Modelling_Date"], '%d/%m/%Y').date(),
                           liability_mode=read_dict.get("liability_mode", "cashflow").strip(),
                           random_seed=int(read_dict.get("random_seed", "42")))

        return setting


def get_unit_linked_policies(filename: str) -> Iterator[UnitLinkedPolicy]:
    """
    Load unit-linked in-force policies from CSV into a UnitLinkedPolicy generator.

    Parameters
    ----------
    filename: string
        Relative path to the unit-linked policies input file

    Returns
    -------
    generator
        Generator yielding one UnitLinkedPolicy instance per CSV row
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            policy = UnitLinkedPolicy(
                policy_id=int(row["Policy_ID"]),
                birth_date=datetime.strptime(row["Birth_Date"], "%d/%m/%Y").date(),
                is_female=bool(int(row["Is_Female"])),
                is_guaranteed=bool(int(row["Is_Guaranteed"])),
                premium=float(row["Premium"]),
                mv=float(row["MV"]),
                gv=float(row["GV"]),
            )
            yield policy


def get_unit_linked_fund(filename: str) -> UnitLinkedFund:
    """
    Load single-pool unit-linked fund parameters from CSV.

    Parameters
    ----------
    filename: string
        Relative path to the unit-linked fund input file

    Returns
    -------
    UnitLinkedFund
        Fund parameters from the first CSV data row
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            return UnitLinkedFund(
                fund_id=int(row["Fund_ID"]),
                lapse_rate=float(row["Lapse_Rate"]),
                admin_fee=float(row["Admin_Fee"]),
                entry_fee=float(row["Entry_Fee"]),
                premium_growth=float(row["Premium_Growth"]),
            )
    raise ValueError(f"No fund row found in {filename}")


def get_society(filename: str) -> Society:
    """
    Load mortality rates from CSV into a Society object.

    Parameters
    ----------
    filename: string
        Relative path to mortality.csv (AGE, MALE, FEMALE columns)

    Returns
    -------
    Society
        Populated Society with male and female mortality series
    """

    mortality_df = pd.read_csv(filename, encoding="utf-8-sig", index_col="AGE",
                           dtype={"MALE": float, "FEMALE": float})
    return Society(mortality_male=mortality_df["MALE"], mortality_female=mortality_df["FEMALE"])
