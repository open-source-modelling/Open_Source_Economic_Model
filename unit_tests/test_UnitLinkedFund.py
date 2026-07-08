import pytest

from LiabilityClasses import UnitLinkedFund


@pytest.fixture
def sample_fund() -> UnitLinkedFund:
    return UnitLinkedFund(
        fund_id=1,
        lapse_rate=0.03,
        admin_fee=0.005,
        entry_fee=0.02,
        premium_growth=0.02,
    )


def test_construct(sample_fund: UnitLinkedFund) -> None:
    assert sample_fund.fund_id == 1
    assert sample_fund.lapse_rate == 0.03
    assert sample_fund.admin_fee == 0.005
    assert sample_fund.entry_fee == 0.02
    assert sample_fund.premium_growth == 0.02


def test_invalid_lapse_rate() -> None:
    with pytest.raises(ValueError):
        UnitLinkedFund(
            fund_id=1,
            lapse_rate=1.5,
            admin_fee=0.005,
            entry_fee=0.02,
            premium_growth=0.02,
        )


def test_negative_premium_growth() -> None:
    with pytest.raises(ValueError):
        UnitLinkedFund(
            fund_id=1,
            lapse_rate=0.03,
            admin_fee=0.005,
            entry_fee=0.02,
            premium_growth=-0.01,
        )
