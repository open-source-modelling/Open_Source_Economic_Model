from osem.CurvesClass import Curves
import pytest
import datetime
import numpy as np

@pytest.fixture
def curves_1():
    ufr = 0.0345
    precision = 0.0000001
    tau = 0.0001
    initial_date = datetime.date(2023, 12, 1)
    country = "Example country" 
    curves = Curves(ufr, precision, tau, initial_date, country)
    return curves

@pytest.fixture
def term_structure_maturity() -> np.ndarray:
    return np.array([1, 2, 3, 4, 8, 10], dtype=float)

@pytest.fixture
def term_structure_yield() -> np.ndarray:
    return np.array([0.01, 0.012, 0.014, 0.018, 0.023, 0.025], dtype=float)

def test_Initialize():
    ufr = 1
    precision = 1
    tau = 1
    initial_date = datetime.date(2015, 12, 1)
    country = "Land" 
    curves = Curves(ufr, precision, tau, initial_date, country)
    
    assert curves.ufr == ufr
    assert curves.precision == precision
    assert curves.tau == tau
    assert curves.initial_date == initial_date
    assert curves.country == country
 
def test_set_observed(curves_1, term_structure_maturity, term_structure_yield):
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    assert np.array_equal(curves_1.m_obs_ini["Maturity"].values, term_structure_maturity)
    assert np.array_equal(curves_1.r_obs_ini["Yield"].values, term_structure_yield)

def test_calc_fwd_rates(curves_1, term_structure_maturity, term_structure_yield):
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    
    maturity_first = term_structure_maturity[:-1]
    maturity_shift = term_structure_maturity[1:]
    yield_first = term_structure_yield[:-1]
    yield_shift = term_structure_yield[1:]
    curves_1.calc_fwd_rates()

    for iel in range(0,len(yield_shift)-1):
        fwd_temp = (1+yield_shift[iel]) ** maturity_shift[iel] / (1+yield_first[iel])**maturity_first[iel]
        assert curves_1.fwd_rates["Forward"].values[iel+1] == fwd_temp
            
def test_sw_heart(curves_1):
    alpha = 0.05
    u = np.array([0.1,0.2,0.3])
    v = np.array([0.5,0.6,0.9])
    out_1 = curves_1.sw_heart(u,v,alpha)
    out_2 = curves_1.sw_heart(v,u,alpha)
    assert (out_1 == out_2.transpose()).all()

def test_sw_heart_zero(curves_1):
    alpha = 0.05
    u = np.array([0,0,0])
    v = np.array([0.5,0.6,0.9])
    expected = np.array([[0,0,0],[0,0,0],[0,0,0]])
    out_1 = curves_1.sw_heart(u, v, alpha)
    out_2 = curves_1.sw_heart(v, u, alpha)
    out_3 = curves_1.sw_heart(u, u, alpha)
    
    assert out_1 == pytest.approx(expected) # Fix to be approximate
    assert out_2 == pytest.approx(expected) # Fix to be approximate
    assert out_3 == pytest.approx(expected) # Fix to be approximate

def test_sw_calibrate(curves_1):
    r = np.array([0.1, 0.2, 0.3])
    m = np.array([1, 2, 3])
    ufr = 0.035
    alpha = 0.5
    b = curves_1.sw_calibrate(r, m, ufr, alpha)
    expected = [3.25964092, -0.01510795, -1.83196649]
    assert b == pytest.approx(expected)

def test_project_forward_rate_mat(curves_1, term_structure_maturity, term_structure_yield):
    n_year = 3
    input_size = len(term_structure_yield)
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    curves_1.calc_fwd_rates()
    curves_1.project_forward_rate(n_year)
    # .all() with the call: a bare .all asserts a bound method, which is always truthy
    assert (curves_1.m_obs["Maturities_year_0"].values == curves_1.m_obs_ini["Maturity"].values).all()
    assert "Maturities_year_1" in curves_1.m_obs
    assert "Maturities_year_2" in curves_1.m_obs
    assert "Maturities_year_3" not in curves_1.m_obs
    assert len(curves_1.m_obs["Maturities_year_0"].values) == input_size

def test_project_forward_rate_obs(curves_1, term_structure_maturity, term_structure_yield):
    n_year = 3
    input_size = len(term_structure_maturity)
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    curves_1.calc_fwd_rates()
    curves_1.project_forward_rate(n_year)
    # .all() with the call: written as a bare .all this asserted a bound method, which is always
    # truthy, so the projection could drift from the input curve without failing here.
    assert np.allclose(curves_1.r_obs["Yield_year_0"].values,
                       curves_1.r_obs_ini["Yield"].values, rtol=0, atol=1e-12)
    assert "Yield_year_1" in curves_1.r_obs
    assert "Yield_year_2" in curves_1.r_obs
    assert "Yield_year_3" not in curves_1.r_obs
    assert len(curves_1.r_obs["Yield_year_0"].values) == input_size

def test_retrieve_rates_year0_not_flat_ufr(curves_1, term_structure_maturity, term_structure_yield):
    """
    Regression test: retrieve_rates(proj_step=0, ...) used to slice with [:-proj_step],
    and [:-0] is equivalent to [:0] in Python, which discarded the entire calibration
    vector and maturities. That collapsed sw_extrapolate to pure UFR discounting, so the
    year-0 curve came back flat at the UFR for every maturity instead of the calibrated
    term structure.
    """
    n_year = 3
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    curves_1.calc_fwd_rates()
    curves_1.project_forward_rate(n_year)
    curves_1.calibrate_projected(n_year, ini_guess=0.05, end=0.5, max_iter=1000)

    target = np.array([1.0, 3.0, 8.0])
    year0_yields = curves_1.retrieve_rates(0, target, "Yield", 0.0)["Yield"].values

    # Must not have collapsed to a flat line at the UFR
    assert not np.allclose(year0_yields, curves_1.ufr)

    # Must match sw_extrapolate run directly on the full (untruncated) year-0
    # calibration vector and maturities
    calib_b = curves_1.b["Calibration_year_0"].values
    calib_m = curves_1.m_obs["Maturities_year_0"].values
    calib_alpha = curves_1.alpha["Alpha_year_0"][0]
    expected = curves_1.sw_extrapolate(target, calib_m, calib_b, curves_1.ufr, calib_alpha)

    assert year0_yields == pytest.approx(expected)

    # proj_step=1 (unaffected by the bug) must remain internally consistent too:
    # it should use the year-1 calibration vector truncated by exactly 1 element.
    target_1 = curves_1.retrieve_rates(1, target, "Yield", 0.0)["Yield"].values
    calib_b_1 = curves_1.b["Calibration_year_1"].values[:-1]
    calib_m_1 = curves_1.m_obs["Maturities_year_1"].values[:-1]
    calib_alpha_1 = curves_1.alpha["Alpha_year_1"][0]
    expected_1 = curves_1.sw_extrapolate(target, calib_m_1, calib_b_1, curves_1.ufr, calib_alpha_1)
    assert target_1 == pytest.approx(expected_1)


#def test_calibrate_projected(curves_1, term_structure_maturity, term_structure_yield):
#    n_year = 3
#    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
#    curves_1.calc_fwd_rates()
#    curves_1.project_forward_rate(n_year)
#    curves_1


#def test_ProjectSpotRates(curves_1, term_structure_maturity, term_structure_yield):
#    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
#    curves_1.calc_fwd_rates()
#    N = 1
#    curves_1.ProjectSpotRates(N)

#    spot = ((1+curves_1.fwd_rates["Forward"][1:]).cumprod(axis=None)**(1/(term_structure_maturity-1))-1)[1:]-1






def test_projected_one_year_spot_equals_the_one_year_forward(curves_1, term_structure_maturity,
                                                             term_structure_yield):
    """
    The shortest point of the curve projected to year j is, by construction, the 1-year forward
    rate covering that year. project_forward_rate used to add 1 before the cumulative product and
    subtract 2 after it, which is only a first-order approximation of the geometric mean and broke
    this identity. fwd_rates["Forward"] holds 1 + fw, so the forward rate itself is that less one.
    """
    n_year = 4
    curves_1.set_observed_term_structure(maturity_vec=term_structure_maturity,
                                         yield_vec=term_structure_yield)
    curves_1.calc_fwd_rates()
    curves_1.project_forward_rate(n_year)

    forwards = curves_1.fwd_rates["Forward"].values
    for year in range(1, n_year):
        one_year_spot = curves_1.r_obs["Yield_year_" + str(year)].dropna().values[0]
        assert one_year_spot == pytest.approx(forwards[year] - 1, abs=1e-14)


def test_projection_is_steep_curve_safe(curves_1):
    """
    The old first-order approximation drifted with the spread of the forward rates: negligible on
    a flat curve, several basis points on a steep one. Year 0 must reproduce the input curve
    whatever its shape.
    """
    maturities = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    yields = np.array([0.01, 0.02, 0.04, 0.07, 0.09, 0.11])

    curves_1.set_observed_term_structure(maturity_vec=maturities, yield_vec=yields)
    curves_1.calc_fwd_rates()
    curves_1.project_forward_rate(2)

    assert np.allclose(curves_1.r_obs["Yield_year_0"].values, yields, rtol=0, atol=1e-12)


# --- bisection_alpha: the three ways the bracket can sit ------------------------------------
#
# g_alfa returns the gap at the convergence point less tau, and falls as alpha grows. EIOPA asks
# for the smallest alpha with g(alpha) <= tau, so an interval with no sign change means either
# "satisfied everywhere" (answer: the lower bound) or "satisfied nowhere" (no admissible alpha
# in this bracket). The bisection used to walk to the upper bound and return it in both cases.

ALPHA_LO, ALPHA_HI = 0.05, 0.5
ALPHA_PRECISION = 1e-10


@pytest.fixture
def gap_to_close() -> tuple[np.ndarray, np.ndarray]:
    """A curve flat at 3% out to 120 years, below the 3.45% UFR, so the extrapolation has a real
    gap to close and g_alfa changes sign inside [0.05, 0.5]."""
    maturities = np.arange(1.0, 121.0)
    return maturities, np.full(maturities.shape, 0.03)


def _g(curves, m, r, alpha):
    return curves.g_alfa(m, r, curves.ufr, alpha, curves.tau)


def test_bisection_alpha_finds_the_root_when_the_bracket_contains_one(curves_1, gap_to_close):
    m, r = gap_to_close
    curves_1.set_observed_term_structure(maturity_vec=m, yield_vec=r)
    assert _g(curves_1, m, r, ALPHA_LO) > 0 > _g(curves_1, m, r, ALPHA_HI)

    alpha = curves_1.bisection_alpha(ALPHA_LO, ALPHA_HI, m, r, curves_1.ufr, curves_1.tau,
                                     ALPHA_PRECISION, 1000)

    assert ALPHA_LO < alpha < ALPHA_HI
    assert _g(curves_1, m, r, alpha) == pytest.approx(0, abs=1e-8)


def test_bisection_alpha_returns_the_lower_bound_when_the_constraint_always_holds(
        curves_1, term_structure_maturity, term_structure_yield):
    """
    The regression. With this curve the gap stays under tau across the whole bracket, so there is
    no root. The smallest admissible alpha is the lower bound; the old code walked x_start up to
    x_end and returned 0.5, the largest one instead.
    """
    m, r = term_structure_maturity, term_structure_yield
    curves_1.set_observed_term_structure(maturity_vec=m, yield_vec=r)
    assert _g(curves_1, m, r, ALPHA_LO) < 0
    assert _g(curves_1, m, r, ALPHA_HI) < 0

    alpha = curves_1.bisection_alpha(ALPHA_LO, ALPHA_HI, m, r, curves_1.ufr, curves_1.tau,
                                     ALPHA_PRECISION, 1000)

    assert alpha == ALPHA_LO
    assert alpha != ALPHA_HI


def test_bisection_alpha_raises_when_no_alpha_in_the_bracket_is_admissible(curves_1, gap_to_close):
    m, r = gap_to_close
    curves_1.set_observed_term_structure(maturity_vec=m, yield_vec=r)
    narrow_hi = 0.08  # the root for this curve is near 0.093, so the whole bracket violates tau
    assert _g(curves_1, m, r, ALPHA_LO) > 0
    assert _g(curves_1, m, r, narrow_hi) > 0

    with pytest.raises(ValueError) as excinfo:
        curves_1.bisection_alpha(ALPHA_LO, narrow_hi, m, r, curves_1.ufr, curves_1.tau,
                                 ALPHA_PRECISION, 1000)

    assert "no admissible value" in str(excinfo.value)
