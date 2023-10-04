from dataclasses import dataclass

@dataclass
class Liability:
    liability_id: int
    cash_flow_dates: list
    cash_flow_series: list
