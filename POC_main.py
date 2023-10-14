# Main script for POC
from ImportData import GetEquityShare, GetSettings, importSWEiopa, GetCash, GetLiability
from EquityClasses import *
from PathsClasses import Paths
from Curves import Curves
import pandas as pd
import datetime
import os

####### PREPARATION OF ENVIRONMENT #######

paths = Paths() # Object used for folder navigation

# Import run parameters
settings = GetSettings(os.path.join(paths.input,"Parameters_2.csv"))
end_date = settings.modelling_date + relativedelta(years=settings.n_proj_years)

# Import risk free rate curve
[maturities_country, curve_country, extra_param, Qb] = importSWEiopa(settings.EIOPA_param_file,settings.EIOPA_curves_file, settings.country)

# Curves object with information about term structure
curves = Curves(extra_param["UFR"]/100, settings.precision, settings.tau, settings.modelling_date , settings.country)

cash = GetCash(os.path.join(paths.input,"Cash_Portfolio_test.csv"))

# Create generator that contains all equity positions
equity_input_generator = GetEquityShare(os.path.join(paths.input,"Equity_Portfolio_test.csv"))
 
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
#equity_portfolio.save_equity_matrices_to_csv(unique_dividend = unique_list, unique_terminal=unique_terminal_list, dividend_matrix=dividend_dates, terminal_matrix=terminal_dates, paths =paths)

# Load liability cashflows
liabilities = GetLiability(os.path.join(paths.input,"Liability_Cashflow.csv"))

unique_liabilities_list = liabilities.unique_dates_profile(liabilities.cash_flow_dates)

### Prepare initial data frames ###

def equity_portfolio_to_dataframe(equity_portfolio):
    
    asset_keys = equity_portfolio.equity_share.keys()

    market_price_tmp = []
    growth_rate_tmp = []
    asset_id_tmp = []
    for key in asset_keys:
        market_price_tmp.append(equity_portfolio.equity_share[key].market_price)
        growth_rate_tmp.append(equity_portfolio.equity_share[key].growth_rate)
        asset_id_tmp.append(equity_portfolio.equity_share[key].asset_id)

    market_price = pd.DataFrame(data=market_price_tmp, index=asset_id_tmp,columns=[settings.modelling_date])

    growth_rate = pd.DataFrame(data=growth_rate_tmp, index=asset_id_tmp,columns=[settings.modelling_date])

    return [market_price, growth_rate]

[market_price_df, growth_rate_df]=equity_portfolio_to_dataframe(equity_portfolio)

previous_market_value= sum(market_price_df[settings.modelling_date]) # Value of the initial portfolio

#Note that it is assumed liabilities not payed at modelling date

###### ALM FUNCTIONS #####
def create_cashflow_dataframe(cash_flow_dates, unique_dates):
    cash_flows = pd.DataFrame(data=np.zeros((len(cash_flow_dates),len(unique_dates))), columns=unique_dates) # Dataframe of cashflows (clumns are dates, rows, assets)
    counter = 0
    for asset in cash_flow_dates:
        keys = asset.keys()
        for key in keys:
            cash_flows[key].iloc[counter] = asset[key]         
        counter+=1
    return cash_flows

def calculate_expired_dates(list_of_dates, deadline: date):
    expired_dates = []
    for date in list_of_dates:
        if date <=deadline:
            expired_dates.append(date)
    return expired_dates

def set_dates_of_interest(modelling_date, end_date):
    next_date_of_interest = modelling_date

    dates_of_interest = []
    while next_date_of_interest <= end_date:
        next_date_of_interest = next_date_of_interest + datetime.timedelta(days=365)
        dates_of_interest.append(next_date_of_interest)

    return pd.Series(dates_of_interest, name="Dates of interest")

### PREPARE DATA STRUCTURES WITH CASH FLOWS### 
# Dataframe with dividend cash flows
cash_flows = create_cashflow_dataframe(dividend_dates, unique_list)
# Dataframe with terminal cash flows
terminal_cash_flows = create_cashflow_dataframe(terminal_dates, unique_terminal_list)

# DataFrame with liabiliy cash flows
liability_cash_flows = pd.DataFrame(columns=liabilities.cash_flow_dates)
liability_cash_flows.loc[-1] = liabilities.cash_flow_series
liability_cash_flows.index = [liabilities.liability_id]

###### GENERATE VECTOR OF NEXT PERIODS #####
dates_of_interest = set_dates_of_interest(settings.modelling_date, end_date)

###### MOVE TO NEXT PERIOD #####

previous_date_of_interest = settings.modelling_date

for date_of_interest in dates_of_interest.values:
    
    # Move modelling time forward
    time_frac = (date_of_interest - previous_date_of_interest).days/365.5

    # Which dividend dates are expired
    expired_dates = calculate_expired_dates(unique_list, date_of_interest)
    for date in expired_dates: # Sum expired dividend flows
        cash.bank_account +=sum(cash_flows[date])
        cash_flows.drop(columns=date)
        unique_list.remove(date)

    # Which terminal dates are expired
    expired_dates = calculate_expired_dates(unique_terminal_list, date_of_interest)
    for date in expired_dates: # Sum expired terminal flows
        cash.bank_account +=sum(terminal_cash_flows[date])
        terminal_cash_flows.drop(columns=date)
        unique_terminal_list.remove(date)

    # Which liability dates are expired
    expired_dates = calculate_expired_dates(unique_liabilities_list, date_of_interest)
    for date in expired_dates: # Sum expired liability flows
        cash.bank_account -=sum(liability_cash_flows[date])
        liability_cash_flows.drop(columns=date)
        unique_liabilities_list.remove(date)

    # Calculate market value of portfolio after stock growth
    market_price_df[date_of_interest] = market_price_df[previous_date_of_interest]* (1+growth_rate_df[settings.modelling_date])**time_frac

    total_market_value=sum(market_price_df[date_of_interest]) # Total value of portfolio after growth

    #print(total_market_value/previous_market_value-1)
    
    # Trading of assets
    if total_market_value<= 0:
        pass
    elif cash.bank_account<0: # Sell assets   
        percentToSell = min(1,-cash.bank_account/total_market_value) # How much of the portfolio needs to be sold
        market_price_df[date_of_interest] = (1-percentToSell)*market_price_df[date_of_interest] # Sold proportion of existing shares
        cash.bank_account += total_market_value-sum(market_price_df[date_of_interest]) # Add cash to bank account equal to shares sold 
        cash_flows = cash_flows.multiply((1-percentToSell)) # Adjust future dividend flows for new asset allocation
        terminal_cash_flows = terminal_cash_flows.multiply((1-percentToSell)) # Adjust terminal cash flows for new asset allocation
    elif cash.bank_account>0: # Buy assets  
        percentToBuy = min(1,cash.bank_account/total_market_value) # What % of the portfolio is the excess cash
        market_price_df[date_of_interest] = (1+percentToBuy)*market_price_df[date_of_interest] # Bought new shares as proportion of existing shares
        cash.bank_account += total_market_value- sum(market_price_df[date_of_interest]) # Bank account reduced for cash spent on buying shares 
        cash_flows = cash_flows.multiply(1+percentToBuy) # Adjust future dividend flows for new asset allocation
        terminal_cash_flows = terminal_cash_flows.multiply(1+percentToBuy)# Adjust terminal cash flows for new asset allocation
    else: # Remaining cash flow is equal to 0 so no trading needed
        pass

    previous_date_of_interest = date_of_interest
    previous_market_value = sum(market_price_df[date_of_interest])
#print(cash_flows)
#print(market_price)
#print(total_market_value)
#print(sum(market_price[modelling_date_1]))
#print(total_market_value-sum(market_price[modelling_date_1]))
#print(cash.bank_account)