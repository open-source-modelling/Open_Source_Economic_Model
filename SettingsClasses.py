from datetime import datetime as dt, timedelta
from datetime import date


class Settings:
    EIOPA_param_file:str
    EIOPA_curves_file: str
    country: str
    run_type: str
    n_proj_years: int
    precision: float
    tau: float
    compounding: int
    modelling_date: date

    def __init__(self, EIOPA_param_file: str, EIOPA_curves_file: str, country: str, run_type: str, n_proj_years: int, precision: float, tau: float, compounding: int, modelling_date: date):
        self.EIOPA_param_file = EIOPA_param_file
        self.EIOPA_curves_file = EIOPA_curves_file
        self.country = country
        self.run_type = run_type
        self.n_proj_years = int(n_proj_years)
        self.precision = precision
        self.tau = tau
        self.compounding = compounding
        self.modelling_date = modelling_date