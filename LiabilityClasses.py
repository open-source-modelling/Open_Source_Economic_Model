from dataclasses import dataclass
from typing import List
from datetime import date


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
