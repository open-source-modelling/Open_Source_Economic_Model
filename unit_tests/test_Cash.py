import datetime
from CashClass import Cash
import pytest


@pytest.fixture
def cash_position() -> Cash:
    asset_id = 1
    market_price = 126

    cash_position = Cash(asset_id = asset_id, market_price= market_price)
    return cash_position


def test_construct():
    asset_id = 1
    bank_account = 12.6

    test_cash = Cash(asset_id = asset_id,bank_account= bank_account)

    assert test_cash.asset_id == asset_id
    assert test_cash.bank_account == bank_account
    

def test_add():
    asset_id = 1
    bank_account = 12.6
    bank_account_add = 100.0

    test_cash_1 = Cash(asset_id = asset_id,bank_account= bank_account)
    test_cash_1.bank_account += bank_account_add 
    assert test_cash_1.bank_account == bank_account+bank_account_add