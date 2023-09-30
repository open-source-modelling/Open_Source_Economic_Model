# Main script for POC
from ImportData import GetEquityShare, GetSettings
from EquityClasses import *
from PathsClasses import Paths



paths = Paths() # Object used for folder navigation

# Import run parameters

settings = GetSettings(paths.input+"Parameters_2.csv")

# Create generator that contains all equity positions
equity_input_generator = GetEquityShare(paths.input+"Equity_Portfolio_test.csv")

# Create equity portfolio class that will contain all positions
equity_portfolio = EquitySharePortfolio()

# Fill portfolio with positions
for equity_share in equity_input_generator:
    equity_portfolio.add(equity_share)


print(equity_portfolio.equity_share)
print(settings.modelling_date)



