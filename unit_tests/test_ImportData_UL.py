import os

from ImportData import (
    get_configuration,
    get_settings,
    get_unit_linked_policies,
    get_unit_linked_fund,
    get_society,
)


def test_get_settings_ul_fields() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "ALM.ini"), os)
    settings = get_settings(conf.input_parameters)
    assert settings.liability_mode == "cashflow"
    assert settings.random_seed == 42


def test_get_unit_linked_policies() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "ALM.ini"), os)
    policies = list(get_unit_linked_policies(conf.input_unit_linked_policies))
    assert len(policies) == 5
    assert policies[0].policy_id == 1001
    assert policies[1].is_guaranteed is True


def test_get_unit_linked_fund() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "ALM.ini"), os)
    fund = get_unit_linked_fund(conf.input_unit_linked_fund)
    assert fund.fund_id == 1
    assert fund.lapse_rate == 0.03
    assert fund.entry_fee == 0.02


def test_get_society() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "ALM.ini"), os)
    society = get_society(conf.input_mortality)
    assert society.mortality_rate(0, is_female=False) > 0
    assert society.mortality_rate(50, is_female=True) > 0
