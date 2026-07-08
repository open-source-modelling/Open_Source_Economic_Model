from dataclasses import dataclass, field
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
    liability_mode: str = "cashflow"
    random_seed: int = 42
    # Declared here and populated in __post_init__ so static analyzers know the attribute exists
    end_date: date = field(init=False)

    def __post_init__(self) -> None:
        self.end_date = self.modelling_date + relativedelta(years=self.n_proj_years)
        if self.liability_mode not in ("cashflow", "unit_linked"):
            raise ValueError("liability_mode must be 'cashflow' or 'unit_linked'")
