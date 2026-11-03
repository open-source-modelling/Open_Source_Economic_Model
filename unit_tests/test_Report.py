import json
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

import osem.main
from osem.ReportClass import build_report_data, create_report, reconcile_results, render_report


REPO_ROOT = Path(__file__).resolve().parent.parent
DATES = ["2023-04-29", "2024-04-29", "2025-04-29"]
NO_VALUE = float("nan")


def _common_columns() -> dict[str, list[float]]:
    return {
        "Start market value": [NO_VALUE, 900.0, 1020.0],
        "After growth market value": [NO_VALUE, 920.0, 1000.0],
        "Portfolio return": [NO_VALUE, 0.05, 0.05],
        "Dividend cash flow": [NO_VALUE, 10.0, 20.0],
        "Coupon cash flow": [NO_VALUE, 5.0, 0.0],
        "Notional cash flow": [NO_VALUE, 0.0, 50.0],
        "End cash": [100.0, 0.0, 0.0],
        "UL policies in force": [0.0, 0.0, 0.0],
    }


@pytest.fixture
def cashflow_results() -> pd.DataFrame:
    return pd.DataFrame({
        **_common_columns(),
        "End market value": [900.0, 1020.0, 1070.0],
        "Equity market value": [400.0, 450.0, 1000.0],
        "Bond market value": [500.0, 570.0, 70.0],
        "Government bond market value": [200.0, 300.0, 70.0],
        "Corporate bond market value": [300.0, 270.0, 0.0],
        "Cash before trade": [NO_VALUE, 100.0, 70.0],
        "Liability cash flow": [NO_VALUE, -15.0, 0.0],
        "Remaining liability payments": [15.0, 0.0, 0.0],
        "UL reserve": [NO_VALUE] * 3,
    }, index=DATES)


@pytest.fixture
def unit_linked_results() -> pd.DataFrame:
    columns = _common_columns()
    columns["UL policies in force"] = [2.0, 1.0, 0.0]
    return pd.DataFrame({
        **columns,
        "End market value": [900.0, 995.0, 769.5],
        "Equity market value": [400.0, 430.0, 700.0],
        "Bond market value": [500.0, 565.0, 69.5],
        "Government bond market value": [100.0, 200.0, 0.0],
        "Corporate bond market value": [400.0, 365.0, 69.5],
        "Cash before trade": [NO_VALUE, 75.0, -205.5],
        "Liability cash flow": [NO_VALUE] * 3,
        "Remaining liability payments": [NO_VALUE] * 3,
        "UL reserve": [300.0, 268.0, 0.0],
        "UL return credited": [NO_VALUE, 12.0, 10.0],
        "UL gross premium cash flow": [NO_VALUE, 10.0, 5.0],
        "UL entry fee cash flow": [NO_VALUE, 1.0, 0.5],
        "UL admin fee cash flow": [NO_VALUE, 3.0, 2.0],
        "UL mortality cash flow": [NO_VALUE, 0.0, -280.5],
        "UL lapse cash flow": [NO_VALUE, -50.0, 0.0],
        "Company account": [0.0, 4.0, 6.5],
    }, index=DATES)


@pytest.fixture
def policy_history() -> pd.DataFrame:
    return pd.DataFrame([
        {"Date": DATES[0], "Policy_ID": 1, "Is_Guaranteed": False, "Closing_MV": 250.0, "Exit_Type": "", "Amount_Paid": 0.0},
        {"Date": DATES[0], "Policy_ID": 2, "Is_Guaranteed": True, "Closing_MV": 50.0, "Exit_Type": "", "Amount_Paid": 0.0},
        {"Date": DATES[1], "Policy_ID": 1, "Is_Guaranteed": False, "Closing_MV": 268.0, "Exit_Type": "", "Amount_Paid": 0.0},
        {"Date": DATES[1], "Policy_ID": 2, "Is_Guaranteed": True, "Closing_MV": 0.0, "Exit_Type": "Lapse", "Amount_Paid": 50.0},
        {"Date": DATES[2], "Policy_ID": 1, "Is_Guaranteed": False, "Closing_MV": 0.0, "Exit_Type": "Death", "Amount_Paid": 280.5},
    ])


def _report_data(html: str) -> dict:
    return json.loads(html.split("const D = ", 1)[1].split(";\n", 1)[0].replace("<\\/", "</"))


def _checks_by_name(checks: list[dict]) -> dict[str, dict]:
    return {check["name"]: check for check in checks}


def test_build_report_data_cashflow(cashflow_results):
    data = build_report_data(cashflow_results, pd.DataFrame())

    assert data["mode"] == "cashflow"
    assert data["years"] == [2023, 2024, 2025]
    assert data["opening_assets"] == 1000.0
    assert data["closing_assets"] == 1070.0
    assert data["paid_out"] == 15.0
    assert data["obligation"] == [15.0, 0.0, 0.0]
    assert "policies" not in data
    assert [flow["label"] for flow in data["flows"]] == ["Price change", "Dividends", "Coupons", "Liability payments"]


def test_bonds_are_split_into_corporate_and_government(cashflow_results):
    data = build_report_data(cashflow_results, pd.DataFrame())
    assert data["government_bond"] == [200.0, 300.0, 70.0]
    assert data["corporate_bond"] == [300.0, 270.0, 0.0]


def test_results_saved_before_government_bonds_still_build_a_report(cashflow_results):
    # Older Results.csv files have no government or corporate bond column; they held only corporate bonds
    older = cashflow_results.drop(columns=["Government bond market value", "Corporate bond market value"])
    data = build_report_data(older, pd.DataFrame())
    assert data["government_bond"] == [0.0, 0.0, 0.0]
    assert data["corporate_bond"] == [500.0, 570.0, 70.0]
    assert all(check["passed"] for check in data["checks"])


def test_results_saved_before_the_corporate_bond_column_still_build_a_report(cashflow_results):
    # Results.csv files saved between the two columns have only the government bond column
    older = cashflow_results.drop(columns="Corporate bond market value")
    data = build_report_data(older, pd.DataFrame())
    assert data["corporate_bond"] == [300.0, 270.0, 0.0]
    assert all(check["passed"] for check in data["checks"])


def test_price_change_adds_back_bond_redemption(cashflow_results):
    data = build_report_data(cashflow_results, pd.DataFrame())
    price_change = next(flow for flow in data["flows"] if flow["label"] == "Price change")
    assert price_change["values"] == [None, 20.0, 30.0]


def test_annualised_return_compounds(cashflow_results):
    cashflow_results["Portfolio return"] = [NO_VALUE, 0.10, 0.21]
    data = build_report_data(cashflow_results, pd.DataFrame())
    assert data["annualised_return"] == pytest.approx((1.10 * 1.21) ** 0.5 - 1.0)


def test_annualised_return_is_none_when_a_return_is_missing(cashflow_results):
    cashflow_results["Portfolio return"] = [NO_VALUE, NO_VALUE, 0.05]
    assert build_report_data(cashflow_results, pd.DataFrame())["annualised_return"] is None


def test_payment_positions_cashflow(cashflow_results):
    data = build_report_data(cashflow_results, pd.DataFrame())
    assert data["largest_payment_index"] == 1
    assert data["last_payment_index"] == 1


def test_payment_positions_default_to_end_of_run_without_payments(cashflow_results):
    cashflow_results["Liability cash flow"] = [NO_VALUE, 0.0, 0.0]
    data = build_report_data(cashflow_results, pd.DataFrame())
    assert data["last_payment_index"] == 2


def test_build_report_data_unit_linked(unit_linked_results, policy_history):
    data = build_report_data(unit_linked_results, policy_history)

    assert data["mode"] == "unit_linked"
    assert data["paid_out"] == 330.5
    assert data["obligation"] == [300.0, 268.0, 0.0]
    assert data["largest_payment_index"] == 2
    assert data["reserve_movements"]["net_premiums"] == [None, 9.0, 4.5]
    assert data["reserve_movements"]["admin_fees"] == [None, -3.0, -2.0]


def test_policies_keep_their_path_after_exit(unit_linked_results, policy_history):
    policies = build_report_data(unit_linked_results, policy_history)["policies"]

    assert [policy["id"] for policy in policies] == [1, 2]
    assert policies[0]["guaranteed"] is False
    assert policies[0]["values"] == [250.0, 268.0, 0.0]
    assert policies[0]["exit"] == {"index": 2, "type": "Death", "amount": 280.5}
    assert policies[1]["guaranteed"] is True
    assert policies[1]["exit"] == {"index": 1, "type": "Lapse", "amount": 50.0}


def test_reconciliation_passes_on_consistent_results(cashflow_results, unit_linked_results, policy_history):
    assert all(check["passed"] for check in reconcile_results(cashflow_results, pd.DataFrame()))
    checks = reconcile_results(unit_linked_results, policy_history)
    assert len(checks) == 7
    assert all(check["passed"] for check in checks)


def test_reconciliation_catches_bond_types_not_adding_up(cashflow_results):
    cashflow_results.loc[DATES[1], "Corporate bond market value"] = 280.0
    checks = _checks_by_name(reconcile_results(cashflow_results, pd.DataFrame()))
    assert not checks["Corporate and government bonds add up to bond market value"]["passed"]
    assert checks["Government bonds are part of bond market value"]["passed"]


@pytest.mark.parametrize("value", [600.0, -1.0])
def test_reconciliation_catches_government_bonds_outside_bond_value(cashflow_results, value):
    # 600 is more than the 570 of bonds held on that date, and a holding cannot be negative
    cashflow_results.loc[DATES[1], "Government bond market value"] = value
    checks = _checks_by_name(reconcile_results(cashflow_results, pd.DataFrame()))
    assert not checks["Government bonds are part of bond market value"]["passed"]
    assert checks["Equities and bonds add up to market value"]["passed"]


def test_reconciliation_catches_a_wrong_closing_balance(cashflow_results):
    cashflow_results.loc[DATES[2], "End market value"] = 1071.0
    checks = _checks_by_name(reconcile_results(cashflow_results, pd.DataFrame()))
    assert not checks["Asset movements add up to closing assets"]["passed"]
    assert not checks["Equities and bonds add up to market value"]["passed"]


def test_reconciliation_treats_a_missing_value_as_a_failure(cashflow_results):
    cashflow_results.loc[DATES[1], "After growth market value"] = NO_VALUE
    checks = _checks_by_name(reconcile_results(cashflow_results, pd.DataFrame()))
    check = checks["Asset movements add up to closing assets"]
    assert not check["passed"]
    assert check["max_error"] is None


@pytest.mark.parametrize("column, value, failing_check", [
    ("UL reserve", 269.0, "Reserve movements add up to closing reserve"),
    ("UL reserve", 269.0, "Policy values add up to the reserve"),
    ("UL lapse cash flow", -51.0, "Policy exits add up to deaths and lapses"),
])
def test_reconciliation_catches_unit_linked_breaks(unit_linked_results, policy_history, column, value, failing_check):
    unit_linked_results.loc[DATES[1], column] = value
    checks = _checks_by_name(reconcile_results(unit_linked_results, policy_history))
    assert not checks[failing_check]["passed"]


def test_render_report_is_self_contained(unit_linked_results, policy_history):
    html = render_report(build_report_data(unit_linked_results, policy_history))

    assert "__REPORT_DATA__" not in html
    assert "__CHART_LIBRARY__" not in html
    assert "Chart.js v4.4.1" in html
    assert not re.search(r"""<(script|link|img)[^>]+(src|href)=["']?https?:""", html)
    assert _report_data(html)["years"] == [2023, 2024, 2025]


def test_render_report_rejects_nan():
    with pytest.raises(ValueError):
        render_report({"bad": float("nan")})


def test_render_report_cannot_be_closed_by_data(cashflow_results):
    data = build_report_data(cashflow_results, pd.DataFrame())
    data["dates"][0] = "</script>"
    html = render_report(data)
    assert '"</script>"' not in html
    assert _report_data(html)["dates"][0] == "</script>"


def test_create_report_rebuilds_from_saved_files(tmp_path, unit_linked_results, policy_history):
    unit_linked_results.to_csv(tmp_path / "Results.csv")
    policy_history.to_csv(tmp_path / "UL_Policy_History.csv", index=False)

    report_path = create_report(str(tmp_path))

    assert report_path == tmp_path / "Report.html"
    data = _report_data(report_path.read_text(encoding="utf-8"))
    assert data["policies"][1]["exit"]["type"] == "Lapse"
    assert all(check["passed"] for check in data["checks"])


def test_create_report_ignores_older_history_in_cashflow_run(tmp_path, cashflow_results):
    cashflow_results.to_csv(tmp_path / "Results.csv")
    (tmp_path / "UL_Policy_History.csv").write_text("left over from an earlier run", encoding="utf-8")

    report_path = create_report(str(tmp_path))

    assert _report_data(report_path.read_text(encoding="utf-8"))["mode"] == "cashflow"


def test_create_report_flags_failed_check_in_report(tmp_path, cashflow_results):
    cashflow_results.loc[DATES[2], "End market value"] = 1071.0
    cashflow_results.to_csv(tmp_path / "Results.csv")

    data = _report_data(create_report(str(tmp_path)).read_text(encoding="utf-8"))

    assert not all(check["passed"] for check in data["checks"])


def _set_up_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    shutil.copy(REPO_ROOT / "ALM.ini", tmp_path / "ALM.ini")
    shutil.copytree(REPO_ROOT / "Input", tmp_path / "Input")
    (tmp_path / "Output").mkdir()
    # A short horizon keeps the test quick and confirms the report does not assume 50 years
    parameters = tmp_path / "Input" / "Parameters.csv"
    text = parameters.read_text(encoding="utf-8-sig")
    text = re.sub(r"n_proj_years,\s*\d+", "n_proj_years,10", text)
    text = re.sub(r"liability_mode,[^\r\n]*", f"liability_mode,{mode}", text)
    parameters.write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("mode", ["cashflow", "unit_linked"])
def test_main_writes_report(tmp_path, monkeypatch, mode):
    _set_up_run(tmp_path, monkeypatch, mode)

    osem.main.main()

    data = _report_data((tmp_path / "Output" / "Report.html").read_text(encoding="utf-8"))
    assert data["mode"] == mode
    assert len(data["years"]) == 11
    assert all(check["passed"] for check in data["checks"])
    assert (tmp_path / "Output" / "UL_Policy_History.csv").exists() == (mode == "unit_linked")
    results = pd.read_csv(tmp_path / "Output" / "Results.csv", index_col=0)
    assert results["Equity market value"].notna().all()
    assert results["Bond market value"].notna().all()
    assert results.columns[-1] == "Corporate bond market value"


def test_main_writes_report_without_policies(tmp_path, monkeypatch):
    _set_up_run(tmp_path, monkeypatch, "unit_linked")
    policies = tmp_path / "Input" / "Unit_Linked_Policies.csv"
    header = policies.read_text(encoding="utf-8-sig").splitlines()[0]
    policies.write_text(header + "\n", encoding="utf-8")

    osem.main.main()

    history = pd.read_csv(tmp_path / "Output" / "UL_Policy_History.csv")
    assert history.empty
    assert list(history.columns) == ["Date", "Policy_ID", "Is_Guaranteed", "Closing_MV", "Exit_Type", "Amount_Paid"]
    data = _report_data((tmp_path / "Output" / "Report.html").read_text(encoding="utf-8"))
    assert data["mode"] == "unit_linked"
    assert data["policies"] == []
    assert data["paid_out"] == 0.0
    assert all(check["passed"] for check in data["checks"])


def test_main_stops_when_the_assets_run_out(tmp_path, monkeypatch):
    _set_up_run(tmp_path, monkeypatch, "unit_linked")
    # Policy values twenty times the assets: the payouts sell the whole portfolio within a few years
    policies = tmp_path / "Input" / "Unit_Linked_Policies.csv"
    policies.write_text(
        "Policy_ID,Birth_Date,Is_Female,Is_Guaranteed,Premium,MV,GV\n"
        "1001,15/03/1970,1,0,5000,2400000,0\n"
        "1002,22/07/1965,0,1,8000,5000000,4000000\n"
        "1003,10/01/1980,1,0,3000,1500000,0\n"
        "1004,05/11/1955,0,0,6000,3600000,0\n"
        "1005,18/09/1975,1,0,4500,1900000,0\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="The assets ran out on"):
        osem.main.main()

    # The periods up to the shortfall are kept for inspection
    results = pd.read_csv(tmp_path / "Output" / "Results.csv", index_col=0)
    assert 1 < len(results) < 11
    assert results["End market value"].iloc[-1] == pytest.approx(0.0)
    assert results["End cash"].iloc[-1] < 0
