import logging
import numpy as np
import pandas as pd
import numpy.typing as npt
from datetime import date
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Tuple, Iterator
from osem.CurvesClass import Curves
from osem.FrequencyClass import Frequency
from osem.logging_utils import get_file_logger

logger = get_file_logger(__name__, "EquityClasses.log", level=logging.INFO)

@dataclass
class EquityShare:
    asset_id: int
    nace: str
    issuer: Optional[str]
    issue_date: date
    dividend_yield: float  # Yield paid on each dividend date (per payment, not annualised); see dividend_amount
    frequency: Frequency
    units: float
    market_price: float
    growth_rate: float
    spread_country: float
    spread_sector: float
    spread_stress: float

    def __post_init__(self) -> None:
        """
        Check that the share uses one of the supported payment frequencies.

        Parameters
        ----------
        self: EquityShare class

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If frequency is not monthly, quarterly, triannual, biannual or annual
        """
        if self.frequency not in [Frequency.MONTHLY, Frequency.QUARTERLY, Frequency.TRIANNUAL, Frequency.BIANNUAL, Frequency.ANNUAL]:
            raise ValueError("Frequency must be either Monthly, Quarterly, Triannual, Biannual or Annual")
        logger.info("Equity class initiated")

    # @property Look into what property does
#    @tracer
    def dividend_amount(self, market_price: float) -> float:
        """
        Calculate the size of the dividend for a share inside the EquityShare class.
        The dividend amount is equal to the percentage of the market value.

        dividend_yield is the yield paid on each dividend date, whatever the frequency. It is not
        an annualised yield: a share with dividend_yield 0.01 and quarterly frequency pays 1% of
        its market price four times a year (about 4% a year). To model a share with an annual
        dividend yield y paid f times a year, set dividend_yield = y / f.

        Parameters
        ----------
        self: EquityShare class
        :type market_price: float
            The current market price of the equity share 
        
        Returns
        -------
        :type dividend_size: float 
            The monetary amount of the dividend
        """
        dividend_size = market_price * self.dividend_yield
        return dividend_size

#    @tracer
    def terminal_amount(self, market_price: float) -> float:
        """
        Calculates the terminal value of an equity share. Currently set as the market value.
        
        Parameters
        ----------
        self: EquityShare class
        :type market_price: float
            The current market price of the equity share 
        
        Returns
        -------
        :type terminal_amount: float 
            The monetary amount that can be obtained by selling the share at the end of the modelling window 
        """

        return market_price

#    @tracer
    def generate_market_value(self, modelling_date: date, evaluated_date: date, market_price: float,
                              growth_rate: float) ->float:
        """
        Calculates the market value appreciation of an equity share between two points in time. 

        Parameters
        ----------
        self: EquityShare class
        :type modelling_date: date
            Earlier date of interest 
        :type evaluated_date: date
            Later date of interest 
        :type market_price: float
            The market price of the share at the earlier date 
        :type growth_rate: float
            Assumed annualized growth rate of the issuer 

        Returns
        -------
        :type float
            The market value at the later date of interest 
        """

        t = (evaluated_date - modelling_date).days / 365.25
        return market_price * (1 + growth_rate) ** t

#    @tracer
    def generate_dividend_dates(self, modelling_date: date, end_date: date) -> Iterator[date]:
        """
        Generator yielding the dividend payment dates, counted from the issue date, that fall on
        or after the modelling date and on or before the end date.

        Parameters
        ----------
        self: EquityShare class
        :type modelling_date: date
            The earliest date considered.
        :type end_date: date
            The latest date considered

        Returns
        -------
        Iterator[date]
            Dividend payment dates on or after modelling_date and on or before end_date.
        """
        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.issue_date - delta
        while this_date < end_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date:  # Not interested in past payments
                continue
            if this_date <= end_date:
                yield this_date  # ? What is the advantage of yield here?

    def create_single_cash_flows(self, modelling_date: date, end_date: date, growth_rate: float)->Dict[date, float]:
        """
        Create a dictionary of dividend cash flows using information about an equity share. The 
        return dictionary has dates of the cash flows as keys and monetary amounts as values. 
        
        Parameters
        ----------
        self: EquityShare instance
            The EquityShare instance with the equity position of interest.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).
        :type growth_rate: float
            Annualized growth rate of the equity of interest.
            
        Returns
        -------
        :type dividends: Dict[date, float]
            The dividend amount per unit of the share on each payment date.
        """

        dividend_amount = 0
        dividends: Dict[date, float] = {}
        for dividend_date in self.generate_dividend_dates(modelling_date, end_date):
            if dividend_date in dividends:  # If two cash flows on same date
                pass
                # Do nothing since dividend amounts are calibrated afterwards for equity
                # dividends[dividend_date] = dividend_amount + dividends[dividend_date]
            else:  # New cash flow date
                market_price = self.generate_market_value(modelling_date, dividend_date,
                                                                    self.market_price,
                                                                    growth_rate)
                dividend_amount = self.dividend_amount(market_price=market_price)
                dividends.update({dividend_date: dividend_amount})
        return dividends


    def create_single_terminal(self, modelling_date: date, end_date: date, growth_rate: float)->Dict[date, float]:
        """
        Create a dictionary of terminal cash flows using information about an equity share. The 
        return dictionary has dates of the cash flows as keys and monetary amounts as values. 
        
        Parameters
        ----------
        self: EquityShare instance
            The EquityShare instance with the equity position of interest.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).
        :type growth_rate: float
            Annualized growth rate of the equity of interest.
            
        Returns
        -------
        :type terminals: Dict[date, float]
            A single entry with end_date as the key and the terminal amount per unit of the share
            as the value.
        """

        terminals: Dict[date, float] = {}
        market_price = self.generate_market_value(modelling_date, end_date, self.market_price,
                                                            growth_rate)
        terminal_amount = self.terminal_amount(market_price=market_price)
        terminals.update({end_date: terminal_amount})
        return terminals

    def price_share(self, dividends: Dict[date, float], terminal: Dict[date, float], modelling_date: date, proj_period: int, curves: Curves)->float:
        """
        Calculate the price of an equity share using the yield curve obtained
        from the curves object.  

        Parameters
        ----------
        self: EquityShare instance
            The EquityShare instance with the equity position of interest.
        :type dividends: Dict[date, float]
            A dictionary with dates of dividend cashflows as keys and monetary amounts as values.
        :type terminal: dict
            A dictionary with dates of terminal sale as keys and monetary amounts as values.              
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type proj_period: int
            Which modelling date in dates of interest is the pricing function using.
        :type curves: Curves
            Instance of the Curves class with calibrated term structure.

        Returns
        -------
        :type disc_value: float
            The price of the share.         
        """
        date_frac: List[float] = []
        cash_flow: List[float] = []
        for key, value in dividends.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
            
        for key, value in terminal.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
        
        date_frac_df = pd.DataFrame(data = date_frac, columns = ["Date Fraction"]) # No need for Dataframes. Remove them
        cash_flow_df = pd.DataFrame(data = cash_flow, columns = ["Cash flow"])

        spread = self.spread_country + self.spread_sector+ self.spread_stress

        #discount = curves.retrieve_rates(proj_period, date_frac.iloc[:, 0].to_numpy(), "Discount", spread)
        discount = curves.retrieve_rates(proj_period, np.asarray(date_frac_df.iloc[:, 0], dtype=np.float64), "Discount", spread)

        nodisc_value = np.asarray(cash_flow_df, dtype=np.float64) * np.asarray(discount, dtype=np.float64)
        # np.sum over the whole frame, not the builtin sum: the builtin iterates the rows of a
        # 2-D array and returns one total per column, so it produced a 1-element array rather
        # than a number, and would silently return a vector if the frame ever gained a column.
        disc_value: float = float(np.sum(nodisc_value))
        return disc_value

    def bisection_growth(self, x_start: float, x_end:float, modelling_date:date, end_date:date, proj_period:int, curves: Curves, precision: float, max_iter:int)->float:
        """
        Bisection root finding algorithm for finding the growth rate at which the share's dividends
        and terminal value, discounted with the risk free curve plus the share's spreads, equal
        its market price.

        Parameters
        ----------
        self: EquityShare instance
            The EquityShare instance with the equity position of interest.
        :type x_start: float
            The lower bound of the growth rate. Ex. x_start = -0.1
        :type x_end: float
            The upper bound of the growth rate. Ex. x_end = 0.2
        :type modelling_date: date
            The date at which the share is valued and from which its price is grown.
        :type end_date: date
            The date at which the modelling window closes.
        :type proj_period: int
            Projection year of modelling_date, which selects the projected curve.
        :type curves: Curves
            Instance of the Curves class with calibrated term structure.
        :type precision: float
            Stopping tolerance. A smaller value gives a more accurate result.
        :type max_iter: int
            Maximum number of iterations, to prevent an infinite loop.

        Returns
        -------
        float
            The growth rate that returns the market price.

        Raises
        ------
        ValueError
            If no solution lies between x_start and x_end
        RuntimeError
            If the calibration has not converged after max_iter iterations


        Implemented by Gregor Fabjan from Qnity Consultants on 08/02/2024.
        """
        
        dividends = self.create_single_cash_flows(modelling_date, end_date, x_start)
        terminal = self.create_single_terminal(modelling_date = modelling_date, end_date = end_date, growth_rate = x_start)
        y_start = self.price_share(dividends, terminal, modelling_date, proj_period, curves)-self.market_price

        dividends = self.create_single_cash_flows(modelling_date, end_date, x_end)
        terminal = self.create_single_terminal(modelling_date = modelling_date, end_date = end_date, growth_rate = x_end)
        y_end = self.price_share(dividends, terminal, modelling_date, proj_period, curves)-self.market_price

        if np.abs(y_start) < precision:
            return x_start
        if np.abs(y_end) < precision:
            return x_end  # If final point already satisfies the conditions return end point

        # The price rises monotonically in the growth rate, so a root exists only if the market
        # price lies between the two bracket prices. Without this check the loop below never sees
        # a sign change, walks x_start all the way up to x_end and returns the bracket bound as if
        # it were a calibrated growth rate. The max_iter guard does not catch that: the interval
        # collapses to `precision` in a few dozen halvings, long before max_iter is reached.
        if np.sign(y_start) == np.sign(y_end):
            raise ValueError(
                f"Growth calibration for equity {self.asset_id} has no solution in "
                f"[{x_start}, {x_end}]: the share prices at {y_start + self.market_price:.4f} "
                f"and {y_end + self.market_price:.4f} at those growth rates, but its market price "
                f"is {self.market_price}. Either widen the bracket, or check that dividend_yield "
                f"is the yield paid on each dividend date rather than an annualised one (see "
                f"dividend_amount)."
            )

        i_iter = 0
        while i_iter <= max_iter:
            x_mid = (x_end + x_start) / 2  # calculate mid-point

            dividends = self.create_single_cash_flows(modelling_date, end_date, x_mid)
            terminal = self.create_single_terminal(modelling_date = modelling_date, end_date = end_date, growth_rate = x_mid)
            y_mid = self.price_share(dividends, terminal, modelling_date, proj_period, curves)-self.market_price
            if (y_mid == 0 or (x_end - x_start) / 2 < precision):  # Solution found
                return x_mid
            else:  # Solution not found
                i_iter += 1
                if np.sign(y_mid) == np.sign(
                        y_start):  # If the start point and the middle point have the same sign, then the root must be in the second half of the interval
                    x_start = x_mid
                else:  # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = x_mid
        raise RuntimeError("Growth calibration did not converge")


class EquitySharePortfolio():
    def __init__(self, equity_share: Optional[Dict[int, EquityShare]] = None):
        """
        Initialize the EquitySharePortfolio instance with the given equity shares.

        Parameters
        ----------
        :type equity_share: Optional[Dict[int, EquityShare]]
            The EquityShare instances, keyed by asset_id. If None, the portfolio starts empty.

        Returns
        -------
        None
        """
        logger.info("EquitySharePortfolio initializer called")
        self.equity_share: Dict[int, EquityShare] = equity_share if equity_share is not None else {}

    def is_empty(self) -> bool:
        """
        Check whether the portfolio holds any equity shares.

        Parameters
        ----------
        self: EquitySharePortfolio class instance

        Returns
        -------
        bool
            True if the portfolio has no equity shares
        """
        return len(self.equity_share) == 0

    def add(self, equity_share: EquityShare) -> None:
        """
        Add a new EquityShare to the EquitySharePortfolio instance

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated initial portfolio.
        :type equity_share: EquityShare
            The EquityShare instance representing a single equity instrument.

        """
        self.equity_share.update({equity_share.asset_id: equity_share})

    def create_dividend_flows(self, modelling_date: date, end_date: date) -> Dict[int, Dict[date, float]]:
        """
        Create a dictionary with the dates at which the dividends are paid out and the amounts per unit for
        each equity share in the portfolio, for dates on or after the modelling date but not after the end date.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated initial portfolio.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        :rtype all_dividends
            A dictionary keyed by asset_id. Each value is a dictionary with the dividend dates as keys and the dividend amounts per unit as values.
        """
        all_dividends: Dict[int, Dict[date, float]] = {}
        equity_share: EquityShare
        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]  # Select one asset position
            dividends = equity_share.create_single_cash_flows(modelling_date, end_date, equity_share.growth_rate)
            all_dividends[asset_id] = dividends
        return all_dividends

    def create_terminal_flows(self, modelling_date: date, terminal_date: date) -> Dict[int, Dict[date, float]]:
        """
        Create a dictionary with the terminal date and the terminal amount per unit for each equity share
        in the portfolio. Each share's price is grown from the modelling date to the terminal date.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the market values are grown.
        :type terminal_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        :rtype all_terminals
            A dictionary keyed by asset_id. Each value is a dictionary with the terminal date as the key and the terminal amount per unit as the value.
        """
        all_terminals: Dict[int, Dict[date, float]] = {}
        terminals: Dict[date, float] = {}
        equity_share: EquityShare

        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]
            terminals = equity_share.create_single_terminal(modelling_date=modelling_date, end_date=terminal_date, growth_rate=equity_share.growth_rate)
            all_terminals[asset_id]=terminals
        return all_terminals

    def create_dividend_fractions(self, modelling_date: date, dividend_array: Dict[int, Dict[date, float]]) -> Tuple[List[npt.NDArray[np.float64]], List[npt.NDArray[np.int_]]]:
        """
        Create the list of year-fractions at which each dividend is paid out (compared to the modelling date) and the list of
        positions of those dividends. Only dividends paid after the modelling date are included.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the dividend fraction is calculated.
        :type dividend_array: Dict[int, Dict[date, float]]
            A dictionary keyed by asset_id. Each value is a dictionary with the dates at which the dividend cash flows are paid out as keys
            and the size of the payment in local currency as values.

        Returns
        -------
        :rtype tuple with two lists, each with one numpy array per asset:
            all_date_frac: Each numpy array represents the time fraction
            between the modelling date and the date of the cash flow (ex. 18 months from modelling date is 1.5).
            all_dates_considered: Each numpy array represents the positions, in that asset's dictionary in
            dividend_array, of the dividends paid after the modelling date. No check is made against the end of the modelling window.
        """

        # other counting conventions MISSING
        # Remove numpy arrays in construction

        # Data structures list of lists for dividend payments
        all_date_frac: List[npt.NDArray[np.float64]] = []  # this will save the date fractions of dividends for the portfolio
        all_dates_considered: List[npt.NDArray[np.int_]] = []  # for each asset, the positions of its dividends paid after the modelling date

        for one_dividend_array in dividend_array.values():
            # equity_share = self.equity_share[asset_id]
            #            one_dividend_array = dividend_array[asset_id]

            # Reset objects for the next asset
            equity_date_frac: npt.NDArray[np.float64] = np.array([])  # this will save date fractions of dividends of a single asset
            equity_dates_considered: npt.NDArray[np.int_] = np.array([])  # positions in one_dividend_array of the dividends paid after the modelling date

            dividend_counter = 0  # Position of the current date in one_dividend_array, counting past and future dates

            for one_dividend_date in list(one_dividend_array.keys()):  # for each dividend date of the selected equity
                one_dividend_days = (one_dividend_date - modelling_date).days
                if one_dividend_days > 0:  # dividend date is after the modelling date
                    equity_date_frac = np.append(
                        equity_date_frac, one_dividend_days / 365.25
                    )  # append date fraction
                    equity_dates_considered = np.append(
                        equity_dates_considered, int(dividend_counter)
                    )  # append this dividend's position in one_dividend_array
                dividend_counter += 1
                # else skip
            all_date_frac.append(
                equity_date_frac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            all_dates_considered.append(
                equity_dates_considered.astype(np.int_)
            )  # append which cash flows are after the modelling date

        return (all_date_frac, all_dates_considered)

    def create_terminal_fractions(self, modelling_date: date, terminal_array: Dict[int, Dict[date, float]]) -> Tuple[List[npt.NDArray[np.float64]], List[npt.NDArray[np.int_]]]:
        """
        Create the list of year-fractions at which the terminal amount is paid out (compared to the modelling date) and the list of
        flags showing which terminal dates are after the modelling date

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the terminal fraction is calculated.
        :type terminal_array: Dict[int, Dict[date, float]]
            A dictionary keyed by asset_id. Each value is a dictionary with the date at which the terminal cash flow is paid out as the key
            and the size of the payment in local currency as the value. Only the first date of each asset is used.

        Returns
        -------
        :rtype tuple with two lists, each with one numpy array per asset:
            all_terminal_date_frac: Each numpy array represents the time fraction
            between the modelling date and the terminal date (ex. 18 months from modelling date is 1.5), or is empty if that date is not after the modelling date.
            all_terminal_dates_considered: Each numpy array is a flag: [1] if the
            terminal date of the asset is after the modelling date, otherwise empty. The value is not an index into terminal_array.
        """

        # other counting conventions MISSING
        # Remove numpy arrays in construction

        # Data structures list of lists for dividend payments
        all_terminal_date_frac: List[npt.NDArray[np.float64]] = []  # this will save the date fractions of dividends for the portfolio
        all_terminal_dates_considered: List[npt.NDArray[np.int_]] = []  # for each asset, [1] if its terminal date is after the modelling date, otherwise empty

        for one_terminal_array in terminal_array.values():

            # Reset objects for the next asset
            equity_terminal_date_frac: npt.NDArray[np.float64] = np.array([])  # this will save date fractions of dividends of a single asset
            equity_terminal_dates_considered: npt.NDArray[np.int_] = np.array([])  # [1] if the terminal date is after the modelling date, otherwise empty

            one_dividend_date = list(one_terminal_array.keys())[0]  # for each dividend date of the selected equity
            one_dividend_days = (one_dividend_date - modelling_date).days
            if one_dividend_days > 0:  # if terminal sale date is after modelling date
                equity_terminal_date_frac = np.append(
                    equity_terminal_date_frac, one_dividend_days / 365.25
                )  # append date fraction
                equity_terminal_dates_considered = np.append(
                    equity_terminal_dates_considered, int(1)
                )  # append "is after modelling date" flag
            # else skip
            all_terminal_date_frac.append(
                equity_terminal_date_frac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            all_terminal_dates_considered.append(
                equity_terminal_dates_considered.astype(np.int_)
            )  # append which cash flows are after the modelling date

        return (all_terminal_date_frac, all_terminal_dates_considered)

    def unique_dates_profile(self, cash_flow_profile: Dict[int, Dict[date, float]]) -> List[date]:
        """
        Create a sorted list of dates at which there is a cash-flow event in any of the assets inside the portfolio.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type cash_flow_profile: Dict[int, Dict[date, float]]
            A dictionary keyed by asset_id, containing the date and size of each cash flow of that asset

        Returns
        -------
        :rtype list: list of sorted unique dates containing at least one cash flow
        """

        unique_dates: List[date] = []
        for one_dividend_array in cash_flow_profile.values():
            for one_dividend_date in one_dividend_array.keys():  # for each dividend date of the selected equity
                if one_dividend_date in unique_dates:
                    continue
                unique_dates.append(one_dividend_date)

        return sorted(unique_dates)

    def cash_flow_profile_list_to_matrix(self, cash_flow_profile: Dict[int, Dict[date, float]]) -> Tuple[List[date], npt.NDArray[np.float64]]:
        """
        Convert the cash flows of each asset into a single matrix with one row per asset and one
        column per date.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
        :type cash_flow_profile: Dict[int, Dict[date, float]]
            Cash flow amounts by date for each asset_id

        Returns
        -------
        Tuple[List[date], npt.NDArray[np.float64]]
            The sorted unique dates, and the matrix of cash flows. Rows follow the order of
            cash_flow_profile, columns follow the sorted dates, and dates without a cash flow are 0.
        """
        unique_dates = self.unique_dates_profile(cash_flow_profile)
        width = len(unique_dates)
        height = len(cash_flow_profile)

        cash_flow_matrix = np.zeros((height, width))
        row = 0
        for one_cash_flow_array in cash_flow_profile.values():
            for date_key, value in one_cash_flow_array.items():
                column = unique_dates.index(date_key)
                cash_flow_matrix[row, column] = value
            row += 1
        return (unique_dates, cash_flow_matrix)

    def init_equity_portfolio_to_dataframe(self, modelling_date: date) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Create the initial market price, growth rate and units DataFrames of the portfolio.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
        :type modelling_date: date
            The date used as the name of the single column in each DataFrame

        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
            The market price, growth rate and units DataFrames, each with asset_id as the index
            and values stored as floats.
        """
        asset_keys = self.equity_share.keys()

        market_price_tmp: List[float] = []
        growth_rate_tmp: List[float] = []
        asset_id_tmp: List[int] = []
        units_tmp: List[float] = []
        for key in asset_keys:
            market_price_tmp.append(self.equity_share[key].market_price)
            growth_rate_tmp.append(self.equity_share[key].growth_rate)
            asset_id_tmp.append(self.equity_share[key].asset_id)
            units_tmp.append(self.equity_share[key].units)

        market_price = pd.DataFrame(data=market_price_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)

        growth_rate = pd.DataFrame(data=growth_rate_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)
        
        units = pd.DataFrame(data=units_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)

        return market_price, growth_rate, units