from dataclasses import dataclass
from datetime import datetime as dt, timedelta
from datetime import date

from dateutil.relativedelta import relativedelta


@dataclass
class Settings:
    EIOPA_param_file: str
    EIOPA_curves_file: str
    country: str
    run_type: str
    n_proj_years: int
    precision: float
    tau: float
    compounding: int
    modelling_date: date

    def __post_init__(self, ) -> None:
        self.end_date = self.modelling_date + relativedelta(years=self.n_proj_years)
        pass
        # if self.n_proj_years <= 0:
        #     raise ValueError("n_proj_years must be greater than 0")
        # if self.precision < 0:
        #     raise ValueError("precision must be positive")
