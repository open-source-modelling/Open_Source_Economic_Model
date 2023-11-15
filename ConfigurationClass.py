
class Configuration:
    def __init__(self) -> None:
        self.bond_portfolio: str = ""
        self.trace_enabled: bool = False
        self.logging_level: str = ""
        self.logging_file_name: str = ""
        self.intermediate_path: str = ""
        self.intermediate_enabled: bool = False
        self.intermediate_equity_portfolio: str = ""
        self.intermediate_cash_portfolio: str = ""
        self.input_path: str = ""
        self.input_cash_portfolio: str = ""
        self.input_curves: str = ""
        self.input_equity_portfolio: str = ""
        self.input_bond_portfolio: str = ""
        self.input_param_no_VA: str = ""
        self.input_spread: str = ""
        self.input_parameters: str = ""
        self.input_liability_cashflow: str = ""
