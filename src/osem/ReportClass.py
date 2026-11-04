import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from osem.logging_utils import get_file_logger

logger = get_file_logger(__name__, "ALM.log")

RESULTS_FILE = "Results.csv"
POLICY_HISTORY_FILE = "UL_Policy_History.csv"
REPORT_FILE = "Report.html"
TEMPLATE_FILE = "report_template.html"
CHART_LIBRARY_FILE = "chart.umd.js"
GOVERNMENT_BOND_COLUMN = "Government bond market value"
CORPORATE_BOND_COLUMN = "Corporate bond market value"

# Largest error allowed in a reconciliation, relative to the size of the balance being checked.
# Float64 noise over a 50 year run stays around 1e-13.
RECONCILIATION_TOLERANCE = 1e-9

# Most policies the report draws a lane for. A portfolio can hold tens of thousands, and a lane
# for each makes the page unreadable and its year slider unusably slow.
POLICY_LANES = 50


def _values(column: pd.Series) -> List[Optional[float]]:
    """
    Convert a column into a list for the report, with missing values as None so they are valid JSON.

    Parameters
    ----------
    column: pd.Series
        The values to convert

    Returns
    -------
    List[Optional[float]]
        The values rounded to two decimals, which is finer than anything the report displays
    """
    return [None if pd.isna(value) else round(float(value), 2) for value in column.tolist()]


def _total_assets(results: pd.DataFrame) -> pd.Series:
    """
    Calculate cash plus invested assets at the end of each period.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    pd.Series
        Total assets per date
    """
    return results["End cash"] + results["End market value"]


def _government_bond_value(results: pd.DataFrame) -> pd.Series:
    """
    Get the market value of the government bonds at the end of each period. They are part of Bond
    market value. A Results.csv saved before government bonds were added has no such column and
    held no government bonds, so its value is zero.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    pd.Series
        Government bond market value per date
    """
    if GOVERNMENT_BOND_COLUMN in results.columns:
        return results[GOVERNMENT_BOND_COLUMN]
    return pd.Series(0.0, index=results.index)


def _corporate_bond_value(results: pd.DataFrame) -> pd.Series:
    """
    Get the market value of the corporate bonds at the end of each period. They are part of Bond
    market value. A Results.csv saved before this column was added held only corporate and
    government bonds, so its value is bond market value less government bonds.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    pd.Series
        Corporate bond market value per date
    """
    if CORPORATE_BOND_COLUMN in results.columns:
        return results[CORPORATE_BOND_COLUMN]
    return results["Bond market value"] - _government_bond_value(results)


def _price_change(results: pd.DataFrame) -> pd.Series:
    """
    Calculate the change in invested assets in each period that did not come from trading. A bond
    notional is added back, because a redemption converts market value into cash without any loss.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    pd.Series
        Change in value per date, missing for the opening date
    """
    return results["After growth market value"] + results["Notional cash flow"] - results["Start market value"]


def _is_unit_linked(results: pd.DataFrame) -> bool:
    """
    Tell whether the results come from a unit-linked run, as only those runs record a reserve.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    bool
        True for a unit_linked run, False for a cashflow run
    """
    return bool(results["UL reserve"].notna().any())


def _asset_flows(results: pd.DataFrame, unit_linked: bool) -> Dict[str, pd.Series]:
    """
    List everything that moves total assets in a period, excluding trades, which only swap cash
    for assets.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv
    unit_linked: bool
        True for a unit_linked run

    Returns
    -------
    Dict[str, pd.Series]
        The signed flows per date, keyed by the label shown in the report
    """
    flows = {
        "Price change": _price_change(results),
        "Dividends": results["Dividend cash flow"],
        "Coupons": results["Coupon cash flow"],
    }
    if unit_linked:
        flows["Premiums"] = results["UL gross premium cash flow"]
        flows["Deaths"] = results["UL mortality cash flow"]
        flows["Lapses"] = results["UL lapse cash flow"]
    else:
        flows["Liability payments"] = results["Liability cash flow"]
    return flows


def _reserve_movements(results: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    List everything that moves the unit-linked reserve in a period.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv from a unit_linked run

    Returns
    -------
    Dict[str, pd.Series]
        The signed movements per date, keyed by the name used in the report data
    """
    return {
        "return_credited": results["UL return credited"],
        "net_premiums": results["UL gross premium cash flow"] - results["UL entry fee cash flow"],
        "admin_fees": -results["UL admin fee cash flow"],
        "lapses": results["UL lapse cash flow"],
        "deaths": results["UL mortality cash flow"],
    }


def _annualised_return(results: pd.DataFrame) -> Optional[float]:
    """
    Calculate the compound yearly return of the invested portfolio over the whole run.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv

    Returns
    -------
    Optional[float]
        The annualised return, or None if a period has no return
    """
    returns = results["Portfolio return"].iloc[1:]
    if returns.empty or bool(returns.isna().any()):
        return None
    growth = np.asarray(1.0 + returns, dtype=np.float64)
    return float(np.prod(growth) ** (1.0 / len(growth)) - 1.0)


def _build_policies(results: pd.DataFrame, history: pd.DataFrame, limit: int) -> List[Dict[str, Any]]:
    """
    Arrange the history of the policies with the largest value at the modelling date as one entry
    per policy with a value for every date, largest first. Equal values are ordered by policy id.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv, whose index gives the dates
    history: pd.DataFrame
        The contents of UL_Policy_History.csv
    limit: int
        The most policies to return. Ex. limit = POLICY_LANES

    Returns
    -------
    List[Dict[str, Any]]
        For each policy: id, guaranteed flag, value per date, and its exit if it left
    """
    if history.empty:
        return []
    # Every policy in force at the modelling date has a row on it, so this ranks all of them
    opening = history[history["Date"].astype(str) == str(results.index[0])]
    largest = opening.sort_values(["Closing_MV", "Policy_ID"], ascending=[False, True])["Policy_ID"].head(limit)
    rank = {int(policy_id): position for position, policy_id in enumerate(largest)}

    positions = {date: position for position, date in enumerate(results.index.tolist())}
    policies: Dict[int, Dict[str, Any]] = {}
    for row in history[history["Policy_ID"].isin(list(rank))].to_dict("records"):
        policy = policies.setdefault(int(row["Policy_ID"]), {
            "id": int(row["Policy_ID"]),
            "guaranteed": bool(row["Is_Guaranteed"]),
            "values": [0.0] * len(positions),
            "exit": None,
        })
        position = positions[str(row["Date"])]
        policy["values"][position] = round(float(row["Closing_MV"]), 2)
        if row["Exit_Type"]:
            policy["exit"] = {
                "index": position,
                "type": str(row["Exit_Type"]),
                "amount": round(float(row["Amount_Paid"]), 2),
            }
    return sorted(policies.values(), key=lambda policy: rank[policy["id"]])


def _check(name: str, errors: pd.Series, scale: pd.Series) -> Dict[str, Any]:
    """
    Turn the errors of one reconciliation into a result. A missing value fails the check, because
    it means a number in the balance could not be calculated.

    Parameters
    ----------
    name: str
        What the check confirms, as shown in the report
    errors: pd.Series
        The amount by which the balance fails to add up, per date
    scale: pd.Series
        The size of the balance per date, which the errors are measured against

    Returns
    -------
    Dict[str, Any]
        The name, whether the check passed, and the largest relative error if there is one
    """
    relative = errors.abs() / scale.abs().clip(lower=1.0)
    complete = not bool(relative.isna().any())
    largest = float(relative.max()) if complete and not relative.empty else None
    passed = complete and (largest is None or largest <= RECONCILIATION_TOLERANCE)
    return {"name": name, "passed": passed, "max_error": largest}


def reconcile_results(results: pd.DataFrame, history: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Confirm that the numbers shown in the report add up. Uses the unrounded results.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv
    history: pd.DataFrame
        The contents of UL_Policy_History.csv, empty for a cashflow run

    Returns
    -------
    List[Dict[str, Any]]
        One result per check
    """
    unit_linked = _is_unit_linked(results)
    total = _total_assets(results)
    closing = total.iloc[1:]
    government = _government_bond_value(results)
    corporate = _corporate_bond_value(results)

    flows = sum(flow.iloc[1:] for flow in _asset_flows(results, unit_linked).values())
    checks = [
        _check("Asset movements add up to closing assets", total.shift(1).iloc[1:] + flows - closing, closing),
        _check(
            "Equities and bonds add up to market value",
            results["Equity market value"] + results["Bond market value"] - results["End market value"],
            results["End market value"],
        ),
        _check(
            "Corporate and government bonds add up to bond market value",
            corporate + government - results["Bond market value"],
            results["Bond market value"],
        ),
        # With the check above, a government value outside [0, bond market value] means a
        # negative corporate holding, which the chart would draw below zero
        _check(
            "Government bonds are part of bond market value",
            (government - results["Bond market value"]).clip(lower=0.0) + (-government).clip(lower=0.0),
            results["Bond market value"],
        ),
    ]

    if unit_linked:
        reserve = results["UL reserve"]
        movements = sum(movement.iloc[1:] for movement in _reserve_movements(results).values())
        checks.append(_check(
            "Reserve movements add up to closing reserve",
            reserve.shift(1).iloc[1:] + movements - reserve.iloc[1:],
            reserve.shift(1).iloc[1:],
        ))

        by_date = history.groupby("Date")
        values = by_date["Closing_MV"].sum().reindex(results.index, fill_value=0.0)
        paid = by_date["Amount_Paid"].sum().reindex(results.index, fill_value=0.0)
        checks.append(_check("Policy values add up to the reserve", values - reserve, reserve))
        outflows = (results["UL mortality cash flow"] + results["UL lapse cash flow"]).iloc[1:]
        checks.append(_check(
            "Policy exits add up to deaths and lapses",
            paid.iloc[1:] + outflows,
            reserve.shift(1).iloc[1:],
        ))
    return checks


def build_report_data(results: pd.DataFrame, history: pd.DataFrame) -> Dict[str, Any]:
    """
    Arrange the saved results into the structure that the report page draws from.

    Parameters
    ----------
    results: pd.DataFrame
        The contents of Results.csv, indexed by date as text (YYYY-MM-DD)
    history: pd.DataFrame
        The contents of UL_Policy_History.csv, empty for a cashflow run

    Returns
    -------
    Dict[str, Any]
        All the values the report needs, ready to be saved as JSON
    """
    unit_linked = _is_unit_linked(results)
    total = _total_assets(results)
    flows = _asset_flows(results, unit_linked)

    if unit_linked:
        payouts = (results["UL mortality cash flow"].fillna(0.0) + results["UL lapse cash flow"].fillna(0.0))
    else:
        payouts = results["Liability cash flow"].fillna(0.0)
    paid_positions = [position for position, payout in enumerate(payouts.tolist()) if payout != 0.0]
    last_index = len(results) - 1

    data: Dict[str, Any] = {
        "mode": "unit_linked" if unit_linked else "cashflow",
        "dates": results.index.tolist(),
        "years": [int(str(date)[:4]) for date in results.index.tolist()],
        "opening_assets": round(float(total.iloc[0]), 2),
        "closing_assets": round(float(total.iloc[-1]), 2),
        "paid_out": round(-sum(payouts.tolist()), 2),
        "annualised_return": _annualised_return(results),
        # The report opens on the year with the largest payment, as it shows the most activity
        "largest_payment_index": int(np.argmin(np.asarray(payouts, dtype=np.float64))) if paid_positions else last_index,
        "last_payment_index": paid_positions[-1] if paid_positions else last_index,
        "equity": _values(results["Equity market value"]),
        "corporate_bond": _values(_corporate_bond_value(results)),
        "government_bond": _values(_government_bond_value(results)),
        "cash": _values(results["End cash"]),
        "total": _values(total),
        "cash_before_trade": _values(results["Cash before trade"]),
        "obligation": _values(results["UL reserve"] if unit_linked else results["Remaining liability payments"]),
        "flows": [{"label": label, "values": _values(flow)} for label, flow in flows.items()],
    }

    if unit_linked:
        data["reserve_movements"] = {name: _values(movement) for name, movement in _reserve_movements(results).items()}
        data["company_account"] = _values(results["Company account"])
        data["policies_in_force"] = _values(results["UL policies in force"])
        data["policies"] = _build_policies(results, history, POLICY_LANES)
        data["policies_total"] = int(history["Policy_ID"].nunique()) if not history.empty else 0

    data["checks"] = reconcile_results(results, history)
    return data


def render_report(data: Dict[str, Any]) -> str:
    """
    Fill the report template with the data and the chart library, so that the page is a single file
    that opens without an internet connection.

    Parameters
    ----------
    data: Dict[str, Any]
        The output of build_report_data

    Returns
    -------
    str
        The complete HTML page
    """
    package_folder = Path(__file__).parent
    template = (package_folder / TEMPLATE_FILE).read_text(encoding="utf-8")
    chart_library = (package_folder / CHART_LIBRARY_FILE).read_text(encoding="utf-8")
    # allow_nan=False rejects a stray NaN, which would otherwise make the page's script invalid.
    # Escaping "</" stops any text in the data from closing the script block early.
    report_data = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return template.replace("__REPORT_DATA__", report_data).replace("__CHART_LIBRARY__", chart_library)


def create_report(output_path: str) -> Path:
    """
    Write Report.html from the results saved in the output folder. Only reads those files, so a
    report can also be rebuilt later without running the model again.

    Parameters
    ----------
    output_path: str
        The folder that holds Results.csv, and UL_Policy_History.csv for a unit_linked run

    Returns
    -------
    Path
        The location of the report
    """
    output_folder = Path(output_path)
    results = pd.read_csv(output_folder / RESULTS_FILE, index_col=0)
    results.index = results.index.map(str)

    # Read only for a unit_linked run, as a cashflow run can leave an older history file in the folder
    history = pd.DataFrame()
    if _is_unit_linked(results):
        history = pd.read_csv(output_folder / POLICY_HISTORY_FILE, keep_default_na=False)

    data = build_report_data(results, history)
    for check in data["checks"]:
        if not check["passed"]:
            logger.warning("Report check failed: %s (largest relative error %s)", check["name"], check["max_error"])

    report_path = output_folder / REPORT_FILE
    report_path.write_text(render_report(data), encoding="utf-8")
    return report_path
