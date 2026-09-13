
class Configuration:
    base_folder: str
    bond_portfolio: str
    trace_enabled: bool
    logging_level: str
    logging_file_name: str
    intermediate_path: str
    intermediate_enabled: bool
    intermediate_cash_portfolio: str
    intermediate_equity_portfolio: str
    intermediate_equity_portfolio_file: str
    intermediate_bond_portfolio_file: str
    input_path: str
    input_cash_portfolio: str
    input_curves: str
    input_equity_portfolio: str
    input_bond_portfolio: str
    input_param_no_VA: str
    input_spread: str
    input_parameters: str
    input_liability_cashflow: str
    input_mortality: str
    input_unit_linked_policies: str
    input_unit_linked_fund: str
    output_path: str

    def __init__(self) -> None:
        self.base_folder: str = ""
        self.bond_portfolio: str = ""
        self.trace_enabled: bool = False
        self.logging_level: str = ""
        self.logging_file_name: str = ""
        self.intermediate_path: str = ""
        self.intermediate_enabled: bool = False
        self.intermediate_cash_portfolio: str = ""
        self.intermediate_equity_portfolio: str = ""
        self.intermediate_equity_portfolio_file: str = ""
        self.intermediate_bond_portfolio_file: str = ""
        self.input_path: str = ""
        self.input_cash_portfolio: str = ""
        self.input_curves: str = ""
        self.input_equity_portfolio: str = ""
        self.input_bond_portfolio: str = ""
        self.input_param_no_VA: str = ""
        self.input_spread: str = ""
        self.input_parameters: str = ""
        self.input_liability_cashflow: str = ""
        self.input_mortality: str = ""
        self.input_unit_linked_policies: str = ""
        self.input_unit_linked_fund: str = ""
        self.output_path: str = ""
