import pandas as pd
import csv
from BondClasses import CorpBond
from EquityClasses import EquityShare
from datetime import datetime

def importSWEiopa(selected_param_file, selected_curves_file, country):
    param_raw = pd.read_csv(selected_param_file, sep=",", index_col=0)
    maturities_country_raw = param_raw.loc[:, country + "_Maturities"].iloc[6:]
    param_country_raw = param_raw.loc[:, country + "_Values"].iloc[6:]
    extra_param = param_raw.loc[:, country + "_Values"].iloc[:6]
    relevant_positions = pd.notna(maturities_country_raw.values)
    maturities_country = maturities_country_raw.iloc[relevant_positions]
    Qb = param_country_raw.iloc[relevant_positions]
    curve_raw = pd.read_csv(selected_curves_file, sep=",", index_col=0)
    curve_country = curve_raw.loc[:, country]
    return [maturities_country, curve_country, extra_param, Qb]


def GetCorporateBonds(filename) -> CorpBond:
    with open(filename, mode="r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            corp_bond = CorpBond(asset_id=int(row["Asset_ID"]),
                                 nace=row["NACE"],
                                 issuer=None,
                                 issue_date=datetime.strptime(row["Issue_Date"], "%d/%m/%Y").date(),
                                 maturity_date=datetime.strptime(row["Maturity_Date"], "%d/%m/%Y").date(),
                                 coupon_rate=float(row["Coupon_Rate"]),
                                 notional_amount=float(row["Notional_Amount"]),
                                 frequency=int(row["Frequency"]),
                                 recovery_rate=float(row["Recovery_Rate"]),
                                 default_probability=float(row["Default_Probability"]),
                                 market_price=float(row["Market_Price"]))
            yield corp_bond



def GetEquityShare(filename:str) -> EquityShare:
    """
    :type filename: str
    """

    with open(filename, mode="r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            equity_share = EquityShare(asset_id=int(row["Asset_ID"]),
                             nace=row["NACE"],
                             issuer=None,
                             issue_date=datetime.strptime(row["Issue_Date"], "%d/%m/%Y").date(),
                             dividend_yield=float(row["Dividend_Yield"]),
                             frequency=int(row["Frequency"]),
                             market_price=float(row["Market_Price"]),
                             growth_rate= float(row["Growth_Rate"]))
            yield equity_share
            
            