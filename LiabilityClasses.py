from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import date
import math

import pandas as pd


@dataclass
class Liability:
    liability_id: int
    cash_flow_dates: List[date]
    cash_flow_series: List[float]

    def unique_dates_profile(self) -> List[date]:

        # define list of unique dates (preserve original order)
        unique_dates: List[date] = []
        for one_dividend_date in self.cash_flow_dates:  # for each dividend date of the selected equity
            if one_dividend_date in unique_dates:  # If two cash flows on same date
                # Do nothing since amounts are calibrated elsewhere
                continue
            unique_dates.append(one_dividend_date)

        return unique_dates


@dataclass(frozen=True)
class UnitLinkedPolicy:
    """
    Static metadata and opening account values for one unit-linked policy.

    Parameters
    ----------
    :type policy_id: int
        Unique policy identifier.
    :type birth_date: date
        Policyholder date of birth.
    :type is_female: bool
        Sex for mortality table lookup.
    :type is_guaranteed: bool
        Whether guaranteed value (GV) is tracked and capitalized.
    :type premium: float
        Opening annual premium amount.
    :type mv: float
        Opening account / market value.
    :type gv: float
        Opening guaranteed value (0 if not guaranteed).
    """

    policy_id: int
    birth_date: date
    is_female: bool
    is_guaranteed: bool
    premium: float
    mv: float
    gv: float

    def __post_init__(self) -> None:
        if self.policy_id <= 0:
            raise ValueError("Policy ID must be greater than 0")
        if self.premium < 0:
            raise ValueError("Premium cannot be negative")
        if self.mv < 0:
            raise ValueError("Market value cannot be negative")
        if self.gv < 0:
            raise ValueError("Guaranteed value cannot be negative")

    def age_at(self, as_of: date) -> int:
        """
        Age in completed years at as_of, using days / 365.25.

        Parameters
        ----------
        :type as_of: date
            Valuation date.

        Returns
        -------
        :rtype: int
            Floor age in years (non-negative).
        """
        age = math.floor((as_of - self.birth_date).days / 365.25)
        return max(0, age)


@dataclass(frozen=True)
class UnitLinkedFund:
    """
    Single-pool fund parameters for unit-linked business.

    Parameters
    ----------
    :type fund_id: int
        Fund identifier (single pool MVP uses one row).
    :type lapse_rate: float
        Annual lapse probability in [0, 1].
    :type admin_fee: float
        Annual admin fee as a proportion of MV in [0, 1].
    :type entry_fee: float
        Entry fee as a proportion of gross premium in [0, 1].
    :type premium_growth: float
        Annual premium growth rate (non-negative).
    """

    fund_id: int
    lapse_rate: float
    admin_fee: float
    entry_fee: float
    premium_growth: float

    def __post_init__(self) -> None:
        if self.fund_id <= 0:
            raise ValueError("Fund ID must be greater than 0")
        if not 0 <= self.lapse_rate <= 1:
            raise ValueError("Lapse rate must be between 0 and 1")
        if not 0 <= self.admin_fee <= 1:
            raise ValueError("Admin fee must be between 0 and 1")
        if not 0 <= self.entry_fee <= 1:
            raise ValueError("Entry fee must be between 0 and 1")
        if self.premium_growth < 0:
            raise ValueError("Premium growth cannot be negative")


class UnitLinkedPortfolio:
    """
    Portfolio wrapper for unit-linked policies keyed by policy_id.
    """

    def __init__(self, policies: Optional[Dict[int, UnitLinkedPolicy]] = None) -> None:
        """
        Parameters
        ----------
        :type policies: dict[int, UnitLinkedPolicy]
            Mapping of policy_id to UnitLinkedPolicy.
        """
        self.policies = policies if policies is not None else {}

    def IsEmpty(self) -> bool:
        """
        Returns
        -------
        :rtype: bool
            True if the portfolio has no policies.
        """
        return len(self.policies) == 0

    def add(self, policy: UnitLinkedPolicy) -> None:
        """
        Add or replace a policy in the portfolio.

        Parameters
        ----------
        :type policy: UnitLinkedPolicy
            Policy instance to insert.
        """
        self.policies[policy.policy_id] = policy

    def init_policy_state_to_dataframe(
        self, modelling_date: date
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Build initial MV, GV, premium, and active-flag DataFrames for modelling_date.

        Parameters
        ----------
        :type modelling_date: date
            Opening modelling date column.

        Returns
        -------
        :rtype: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]
            ul_mv_df, ul_gv_df, ul_premium_df, ul_active_df
            (rows = policy_id, columns = dates).
        """
        policy_ids: List[int] = []
        mv_tmp: List[float] = []
        gv_tmp: List[float] = []
        premium_tmp: List[float] = []
        active_tmp: List[float] = []

        for policy_id in sorted(self.policies.keys()):
            policy = self.policies[policy_id]
            policy_ids.append(policy_id)
            mv_tmp.append(policy.mv)
            gv_tmp.append(policy.gv)
            premium_tmp.append(policy.premium)
            active_tmp.append(1.0)

        ul_mv_df = pd.DataFrame(data=mv_tmp, index=policy_ids, columns=[modelling_date])
        ul_gv_df = pd.DataFrame(data=gv_tmp, index=policy_ids, columns=[modelling_date])
        ul_premium_df = pd.DataFrame(data=premium_tmp, index=policy_ids, columns=[modelling_date])
        ul_active_df = pd.DataFrame(data=active_tmp, index=policy_ids, columns=[modelling_date])

        return ul_mv_df, ul_gv_df, ul_premium_df, ul_active_df

    def total_reserve(self, mv_df: pd.DataFrame, active_df: pd.DataFrame, as_of: date) -> float:
        """
        Sum MV over active policies at as_of.

        Parameters
        ----------
        :type mv_df: pd.DataFrame
            Market-value state matrix.
        :type active_df: pd.DataFrame
            Active flags (1 = in force).
        :type as_of: date
            Column date.

        Returns
        -------
        :rtype: float
            Total UL reserve.
        """
        return float((mv_df[as_of] * active_df[as_of]).sum())
