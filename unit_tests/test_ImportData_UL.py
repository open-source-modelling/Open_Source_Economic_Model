import os

from ImportData import (
    get_configuration,
    get_settings,
    get_unit_linked_policies,
    get_unit_linked_fund,
    get_society,
)


def test_get_unit_linked_policies() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "unit_tests", "fixed_settings", "ALM.ini"), os)
    policies = list(get_unit_linked_policies(conf.input_unit_linked_policies))
    assert len(policies) == 5
    assert policies[0].policy_id == 1001
    assert policies[1].is_guaranteed is True


def test_get_unit_linked_fund() -> None:
    base = os.getcwd()
    conf = get_configuration(os.path.join(base, "unit_tests", "fixed_settings", "ALM.ini"), os)
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


def test_get_settings_liability_mode_present(tmp_path):

    params_file = tmp_path / "Parameters.csv"
    params_file.write_text(
        "Parameter,Value\n"
        "EIOPA_param_file,Input/Param_no_VA.csv\n"
        "EIOPA_curves_file,Input/Curves_no_VA.csv\n"
        "country,Slovenia\n"
        "run_type,Risk Neutral\n"
        "n_proj_years,50\n"
        "Precision,1E-10\n"
        "Tau,0.0001\n"
        "compounding,-1\n"
        "Modelling_Date,29/04/2023\n"
        "liability_mode,unit_linked\n"
        "random_seed,7\n"
    )
    settings = get_settings(str(params_file))
    assert settings.liability_mode == "unit_linked"
    assert settings.random_seed == 7


def test_get_settings_liability_mode_defaults_to_cashflow(tmp_path):
    params_file = tmp_path / "Parameters.csv"
    params_file.write_text(  # same content, but no liability_mode row at all
        "Parameter,Value\n"
        "EIOPA_param_file,Input/Param_no_VA.csv\n"
        "EIOPA_curves_file,Input/Curves_no_VA.csv\n"
        "country,Slovenia\n"
        "run_type,Risk Neutral\n"
        "n_proj_years,50\n"
        "Precision,1E-10\n"
        "Tau,0.0001\n"
        "compounding,-1\n"
        "Modelling_Date,29/04/2023\n"
    )
    settings = get_settings(str(params_file))
    assert settings.liability_mode == "cashflow"

