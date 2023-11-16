from CurvesClass import Curves
import pytest
import datetime



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
 


