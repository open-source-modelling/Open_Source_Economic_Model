from CurvesClass import Curves
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
def term_structure_maturity():
    maturity_vec = [1, 2, 3, 4, 8, 10]
    return maturity_vec

@pytest.fixture
def term_structure_yield():
    yield_vec = [0.01, 0.012, 0.014, 0.018, 0.023,0.025]
    return yield_vec

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
    curves_1.SetObservedTermStructure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    assert all(curves_1.m_obs["Maturity"].values == term_structure_maturity)
    assert all(curves_1.r_obs["Yield"].values == term_structure_yield)

def test_CalcFwdRates(curves_1, term_structure_maturity, term_structure_yield):
    curves_1.SetObservedTermStructure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
    
    maturity_first = term_structure_maturity[:-1]
    maturity_shift = term_structure_maturity[1:]
    yield_first = term_structure_yield[:-1]
    yield_shift = term_structure_yield[1:]
    curves_1.CalcFwdRates()

    for iel in range(0,len(yield_shift)-1):
        fwd_temp = (1+yield_shift[iel]) ** maturity_shift[iel] / (1+yield_first[iel])**maturity_first[iel]
        assert curves_1.fwd_rates["Forward"].values[iel+1] == fwd_temp
            
def test_SWHeart(curves_1):
    alpha = 0.05
    u = np.array([0.1,0.2,0.3])
    v = np.array([0.5,0.6,0.9])
    out_1 = curves_1.SWHeart(u,v,alpha)
    out_2 = curves_1.SWHeart(v,u,alpha)
    assert (out_1 == out_2.transpose()).all()






#def test_ProjectSpotRates(curves_1, term_structure_maturity, term_structure_yield):
#    curves_1.SetObservedTermStructure(maturity_vec=term_structure_maturity, yield_vec=term_structure_yield)
#    curves_1.CalcFwdRates()
#    N = 1
#    curves_1.ProjectSpotRates(N)

#    spot = ((1+curves_1.fwd_rates["Forward"][1:]).cumprod(axis=None)**(1/(term_structure_maturity-1))-1)[1:]-1




