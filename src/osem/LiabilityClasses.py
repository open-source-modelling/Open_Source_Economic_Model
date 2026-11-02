from dataclasses import dataclass
from typing import List
from datetime import date

@dataclass
class Liability:
    liability_id: int
    cash_flow_dates: List[date]
    cash_flow_series: List[float]

    def unique_dates_profile(self) -> List[date]:
        """
        Create a list of the dates at which the liability has a cash flow. A date that appears
        more than once is listed once, and the dates keep their original order rather than being
        sorted.

        Parameters
        ----------
        self: Liability instance
            The Liability instance with populated cash flow dates.

        Returns
        -------
        List[date]
            The unique cash flow dates, in the order they first appear in cash_flow_dates.
        """

        # define list of unique dates (preserve original order)
        unique_dates: List[date] = []
        for cash_flow_date in self.cash_flow_dates:
            if cash_flow_date in unique_dates:  # If two cash flows on same date
                # Do nothing since create_liabilities_df adds their amounts together
                continue
            unique_dates.append(cash_flow_date)

        return unique_dates
