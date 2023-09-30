# Main script for POC
from ImportData import GetEquityShare
from EquityClasses import *
from PathsClasses import Paths

paths = Paths() # Object used for folder navigation

equity_input_generator = GetEquityShare(paths.input+"Equity_Portfolio_test.csv")

equity_portfolio = EquitySharePortfolio()

for equity_share in equity_input_generator:
    equity_portfolio.add(equity_share)

print(equity_portfolio.equity_share)




