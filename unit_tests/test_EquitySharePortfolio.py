from EquityClasses import Frequency, EquityShare, EquitySharePortfolio
import pytest
import datetime


@pytest.fixture
def equity_share_1() -> EquityShare:
    asset_id = 1
    nace = "A.1.2"
    issuer = "Open Source Modelling"
    buy_date = datetime.date(2015, 12, 1)
    dividend_yield = 0.03
    frequency = Frequency.QUARTERLY
    market_price = 12.6

    equity_share_1 = EquityShare(asset_id = asset_id
        , nace= nace
        ,issuer= issuer
        ,buy_date= buy_date
        ,dividend_yield= dividend_yield
        ,frequency= frequency
        ,market_price= market_price
    )

    return equity_share_1


@pytest.fixture()
def equity_share_2() -> EquityShare:
    equity_share_2 = EquityShare(asset_id= 2
        , nace= "A.3.1"
        ,issuer= "Test Issuer"
        ,buy_date= datetime.date(2016, 7, 1)
        ,dividend_yield= 0.04
        ,frequency= Frequency.MONTHLY
        ,market_price= 102.1
)
    return equity_share_2


def test_IsEmpty():
    equity_share_portfolio = EquitySharePortfolio()
    assert equity_share_portfolio.IsEmpty() == True


def test_Not_IsEmpty(equity_share_1):
    equity_share_portfolio = EquitySharePortfolio({equity_share_1.asset_id: equity_share_1})
    assert equity_share_portfolio.IsEmpty() == False


def test_add_to_empty_portfolio(equity_share_1):
    equity_share_portfolio = EquitySharePortfolio()
    equity_share_portfolio.add(equity_share_1)
    assert equity_share_portfolio.IsEmpty() is False
    assert len(equity_share_portfolio.equity_share) == 1
    assert equity_share_portfolio.equity_share[equity_share_1.asset_id] == equity_share_1
    assert (equity_share_1.asset_id in equity_share_portfolio.equity_share)


def test_add_to_non_empty_portfolio(equity_share_1, equity_share_2):
    equity_share_portfolio = EquitySharePortfolio()
    equity_share_portfolio.add(equity_share_1)
    equity_share_portfolio.add(equity_share_2)

    
    asset_id = 3
    nace = "AB.4"
    issuer= "Test Issuer"
    buy_date= datetime.date(2012, 2, 1)
    dividend_yield= 0.01
    frequency= Frequency.BIANNUAL
    market_price= 90
    
    
    equity_share_3 = EquityShare(
        asset_id
        ,nace
        ,issuer
        ,buy_date
        ,dividend_yield
        ,frequency
        ,market_price)
    equity_share_portfolio.add(equity_share_3)
    assert len(equity_share_portfolio.equity_share) == 3
    assert (equity_share_3.asset_id in equity_share_portfolio.equity_share)


def test_create_dividend_dates_single_bond(equity_share_1):
    equity_share_portfolio = EquitySharePortfolio()
    equity_share_portfolio.add(equity_share_1)
    modelling_date = datetime.date(2023, 6, 1)
    end_date= datetime.date(2023+50, 6, 1)
    dividend_dates = equity_share_portfolio.create_dividend_dates(modelling_date, end_date)

    assert datetime.date(2023, 6, 1) in dividend_dates
    assert datetime.date(2023, 9, 1) in dividend_dates
    assert datetime.date(2023, 12, 1) in dividend_dates
    assert dividend_dates[datetime.date(2023, 6, 1)] == equity_share_1.dividend_amount


def test_create_dividend_dates_two_equities(equity_share_1, equity_share_2):
    equity_share_portfolio = EquitySharePortfolio()
    equity_share_portfolio.add(equity_share_1)
    equity_share_portfolio.add(equity_share_2)
    modelling_date = datetime.date(2023, 6, 1)
    end_date= datetime.date(2023+50, 6, 1)
    dividend_dates = equity_share_portfolio.create_dividend_dates(modelling_date, end_date)

    assert datetime.date(2023, 6, 1) in dividend_dates
    assert dividend_dates[datetime.date(2023, 6, 1)] == equity_share_1.dividend_amount + equity_share_2.dividend_amount
    assert datetime.date(2023, 7, 1) in dividend_dates


#def test_create_terminal_cashflow_single_equities(equity_share_1):
#    equity_share_portfolio = EquitySharePortfolio()
#    equity_share_portfolio.add(equity_share_1)
#    modelling_date = datetime.date(2023, 6, 1)
#    end_date= datetime.date(2023+50, 6, 1)
#    terminal_cashflow = equity_share_portfolio.create_terminal_cashflow(modelling_date, end_date)
#    assert len(terminal_cashflow) == 1
#    assert terminal_cashflow[equity_share_1.terminal_date] == equity_share_1.notional_amount



#def test_create_maturity_cashflow_multiple_bonds(corp_bond_1, corp_bond_2):
#    corporate_bond_portfolio = EquitySharePortfolio()
#    corporate_bond_portfolio.add(corp_bond_1)
#    corporate_bond_portfolio.add(corp_bond_2)
#    modelling_date = datetime.date(2023, 6, 1)
#    maturity_cashflow = corporate_bond_portfolio.create_maturity_cashflow(modelling_date)
#    assert len(maturity_cashflow) == 2
#    assert corp_bond_1.maturity_date in maturity_cashflow
#    assert corp_bond_2.maturity_date in maturity_cashflow
