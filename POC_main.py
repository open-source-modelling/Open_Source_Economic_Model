# Main script for POC
from ImportData import GetEquityShare, GetSettings, importSWEiopa, GetCash, GetLiability
from EquityClasses import *
from PathsClasses import Paths
from Curves import Curves
import pandas as pd
import datetime

paths = Paths() # Object used for folder navigation

# Import run parameters

settings = GetSettings(paths.input+"Parameters_2.csv")
end_date = settings.modelling_date + relativedelta(years=settings.n_proj_years)

# Import risk free rate curve
[maturities_country, curve_country, extra_param, Qb] = importSWEiopa(settings.EIOPA_param_file,settings.EIOPA_curves_file, settings.country)

# Curves object with information about term structure
curves = Curves(extra_param["UFR"]/100, settings.precision, settings.tau, settings.modelling_date , settings.country)

cash = GetCash(paths.input+"Cash_Portfolio_test.csv")

# Create generator that contains all equity positions
equity_input_generator = GetEquityShare(paths.input+"Equity_Portfolio_test.csv")
 
# Create equity portfolio class that will contain all positions
equity_portfolio = EquitySharePortfolio()

# Fill portfolio with equity positions
for equity_share in equity_input_generator:
    equity_portfolio.add(equity_share)

# Calculate cashflow dates based on equity information
dividend_dates = equity_portfolio.create_dividend_dates(settings.modelling_date, end_date)
terminal_dates = equity_portfolio.create_terminal_dates(modelling_date=settings.modelling_date, terminal_date=end_date, terminal_rate=curves.ufr)

# Calculate date fractions based on modelling date
[all_date_frac, all_dates_considered] = equity_portfolio.create_dividend_fractions(settings.modelling_date, dividend_dates) 
[all_dividend_date_frac, all_dividend_dates_considered] = equity_portfolio.create_terminal_fractions(settings.modelling_date, terminal_dates)

unique_list = equity_portfolio.unique_dates_profile(dividend_dates)
unique_terminal_list = equity_portfolio.unique_dates_profile(terminal_dates)

# Save equity cash flows matrices
equity_portfolio.save_equity_matrices_to_csv(unique_dividend = unique_list, unique_terminal=unique_terminal_list, dividend_matrix=dividend_dates, terminal_matrix=terminal_dates, paths =paths)

# Load liability cashflows

liabilities = GetLiability(paths.input+"Liability_Cashflow.csv")

### Market value at modelling date  ###

asset_keys = equity_portfolio.equity_share.keys()

market_price_tmp = []
for key in asset_keys:
    market_price_tmp.append(equity_portfolio.equity_share[key].market_price)

market_price = pd.DataFrame(data=market_price_tmp, index=asset_keys,columns=[settings.modelling_date])
print(sum(market_price[settings.modelling_date]))

# Amount of cash at modelling date
print(cash.bank_account)

# Assume liabilities not payed at modelling date

# Move to next period
modelling_date_1 = settings.modelling_date + datetime.timedelta(days=365)

# Check what cash flows expire between dates
print(modelling_date_1)

cash_flows = pd.DataFrame(data=np.zeros((len(dividend_dates),len(unique_list))),columns=unique_list)

# Dataframe of cashflows (clumns are dates, rows, assets)
counter = 0
for asset in dividend_dates:
    keys = asset.keys()
    for key in keys:
        cash_flows[key].iloc[counter] = asset[key]         
    counter+=1

print(cash_flows)

# Which dates are expired
expired_dates = []
for date in unique_list:
    if date <=modelling_date_1:
        expired_dates.append(date)
print(expired_dates)


# Sum expired cash flows
print(cash.bank_account)
for date in expired_dates:
    cash.bank_account +=sum(cash_flows[date])
    cash_flows.drop(columns=date)

print(cash.bank_account)