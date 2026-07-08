from datetime import date
import random

import pandas as pd
import pytest

from LiabilityClasses import UnitLinkedPolicy, UnitLinkedFund, UnitLinkedPortfolio
from SocietyClass import Society
from MainLoop import (
    capitalize_policies,
    apply_premiums,
    apply_admin_fees,
    apply_mortality,
    apply_lapse,
    process_unit_linked_period,
)


@pytest.fixture
def policies() -> dict[int, UnitLinkedPolicy]:
    p1 = UnitLinkedPolicy(
        policy_id=1,
        birth_date=date(1970, 1, 1),
        is_female=False,
        is_guaranteed=False,
        premium=1000.0,
        mv=100000.0,
        gv=0.0,
    )
    p2 = UnitLinkedPolicy(
        policy_id=2,
        birth_date=date(1965, 1, 1),
        is_female=True,
        is_guaranteed=True,
        premium=2000.0,
        mv=200000.0,
        gv=150000.0,
    )
    return {1: p1, 2: p2}


@pytest.fixture
def fund() -> UnitLinkedFund:
    return UnitLinkedFund(
        fund_id=1,
        lapse_rate=0.03,
        admin_fee=0.005,
        entry_fee=0.02,
        premium_growth=0.02,
    )


@pytest.fixture
def society() -> Society:
    ages = list(range(50, 61))
    male = pd.Series([0.01] * len(ages), index=ages)
    female = pd.Series([0.008] * len(ages), index=ages)
    return Society(mortality_male=male, mortality_female=female)


def _state(previous: date, policies: dict[int, UnitLinkedPolicy]):
    ptf = UnitLinkedPortfolio(policies)
    mv, gv, prem, active = ptf.init_policy_state_to_dataframe(previous)
    return mv, gv, prem, active


def test_capitalize_policies(policies, fund):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)
    mv, gv, _, active = _state(previous, policies)
    active[current] = active[previous]
    mv[current] = mv[previous]
    gv[current] = gv[previous]

    mv, gv = capitalize_policies(mv, gv, active, policies, current, portfolio_return=0.05)

    assert mv.loc[1, current] == pytest.approx(105000.0)
    assert mv.loc[2, current] == pytest.approx(210000.0)
    assert gv.loc[1, current] == pytest.approx(0.0)
    assert gv.loc[2, current] == pytest.approx(157500.0)


def test_apply_premiums(policies, fund):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)
    mv, _, prem, active = _state(previous, policies)
    active[current] = active[previous]
    mv[current] = mv[previous]
    prem[current] = prem[previous]

    time_frac = 1.0
    mv, prem, gross, entry = apply_premiums(mv, prem, active, fund, current, time_frac)

    expected_gross = 1000.0 * 1.02 + 2000.0 * 1.02
    expected_entry = expected_gross * 0.02
    expected_net = expected_gross - expected_entry

    assert gross == pytest.approx(expected_gross)
    assert entry == pytest.approx(expected_entry)
    assert mv.loc[1, current] == pytest.approx(100000.0 + 1000.0 * 1.02 * 0.98)
    assert mv.loc[2, current] == pytest.approx(200000.0 + 2000.0 * 1.02 * 0.98)
    assert expected_net == pytest.approx(
        (mv.loc[1, current] - 100000.0) + (mv.loc[2, current] - 200000.0)
    )


def test_apply_admin_fees_half_year(policies, fund):
    previous = date(2023, 4, 29)
    current = date(2023, 10, 29)
    mv, _, _, active = _state(previous, policies)
    active[current] = active[previous]
    mv[current] = mv[previous]

    time_frac = 0.5
    fee_factor = 1.0 - ((1.0 - 0.005) ** time_frac)
    expected = (100000.0 + 200000.0) * fee_factor

    mv, admin = apply_admin_fees(mv, active, fund, current, time_frac)
    assert admin == pytest.approx(expected)
    assert mv.loc[1, current] == pytest.approx(100000.0 * (1.0 - fee_factor))


def test_apply_mortality_forced_draw(policies, society, fund):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)
    mv, _, _, active = _state(previous, policies)
    active[current] = active[previous]
    mv[current] = mv[previous]

    class AlwaysDie:
        def random(self):
            return 0.0

    mv, active, death, deaths = apply_mortality(
        mv, active, policies, society, current, 1.0, AlwaysDie()
    )
    assert deaths == 2
    assert death == pytest.approx(300000.0)
    assert active.loc[1, current] == 0.0
    assert mv.loc[1, current] == 0.0


def test_apply_lapse_forced_survive(policies, fund):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)
    mv, _, _, active = _state(previous, policies)
    active[current] = active[previous]
    mv[current] = mv[previous]

    class AlwaysSurvive:
        def random(self):
            return 0.99

    mv, active, surrender, lapses = apply_lapse(
        mv, active, fund, current, 1.0, AlwaysSurvive()
    )
    assert lapses == 0
    assert surrender == 0.0
    assert active.loc[1, current] == 1.0


def test_process_unit_linked_period_orchestrator(policies, fund, society):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)
    mv, gv, prem, active = _state(previous, policies)

    class SurviveAll:
        def random(self):
            return 0.99

    mv, gv, prem, active, cfs = process_unit_linked_period(
        current_date=current,
        previous_date=previous,
        portfolio_return=0.05,
        time_frac=1.0,
        mv_df=mv,
        gv_df=gv,
        premium_df=prem,
        active_df=active,
        policies=policies,
        fund=fund,
        society=society,
        random_seed=42,
        proj_period=1,
        rng=SurviveAll(),
    )

    assert cfs["deaths"] == 0
    assert cfs["lapses"] == 0
    assert cfs["in_force"] == 2
    assert cfs["gross_premium"] == pytest.approx(1000.0 * 1.02 + 2000.0 * 1.02)
    assert cfs["entry_fee"] == pytest.approx(cfs["gross_premium"] * 0.02)
    assert mv.loc[1, current] > 0
    assert active.loc[1, current] == 1.0


def test_reproducibility_same_seed(policies, fund, society):
    previous = date(2023, 4, 29)
    current = date(2024, 4, 28)

    def run_once(seed: int):
        mv, gv, prem, active = _state(previous, policies)
        _, _, _, active_out, cfs = process_unit_linked_period(
            current_date=current,
            previous_date=previous,
            portfolio_return=0.05,
            time_frac=1.0,
            mv_df=mv,
            gv_df=gv,
            premium_df=prem,
            active_df=active,
            policies=policies,
            fund=fund,
            society=society,
            random_seed=seed,
            proj_period=1,
        )
        return cfs["deaths"], cfs["lapses"], list(active_out[current].values)

    assert run_once(42) == run_once(42)
