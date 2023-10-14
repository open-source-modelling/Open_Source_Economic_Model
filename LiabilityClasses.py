from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Liability:
    liability_id: int
    cash_flow_dates: list
    cash_flow_series: list

    def unique_dates_profile(self, cashflow_profile: List):

            # define list of unique dates
            unique_dates = []
            for one_dividend_date in cashflow_profile:  # for each dividend date of the selected equity
                if one_dividend_date in unique_dates: # If two cash flows on same date
                    pass
                    # Do nothing since dividend amounts are calibrated afterwards for equity
                    #dividends[dividend_date] = dividend_amount + dividends[dividend_date] # ? Why is here a plus? (you agregate coupon amounts if same date?)
                else: # New cash flow date
                    unique_dates.append(one_dividend_date)

            return unique_dates