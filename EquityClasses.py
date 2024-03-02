from typing import List
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from CurvesClass import Curves
from FrequencyClass import Frequency
from TraceClass import Trace, tracer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])")

file_handler = logging.FileHandler("EquityClasses.log")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

@dataclass
class EquityShare:
    asset_id: int
    nace: str
    issuer: str
    issue_date: date
    dividend_yield: float
    frequency: Frequency
    units: float
    market_price: float
    growth_rate: float

    def __post_init__(self) -> None:
        logger.info("Equity class initiated")

    # @property Look into what property does
    @tracer
    def dividend_amount(self, market_price: float) -> float:
        """
        Calculate the size of the dividend for a share inside the EquityShare class.
        The dividend amount is equal to the percentage of the market value.
        
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

    @tracer
    def terminal_amount(self, market_price: float, growth_rate: float, terminal_rate: float) -> float:
        """
        Calculates the terminal value of an equity share. Currently set as the market value.
        
        Parameters
        ----------
        self: EquityShare class
        :type market_price: float
            The current market price of the equity share 
        :type growth_rate: float
            The annual growth rate of the particular stock
        :type terminal_rate: float
            The assumed terminal interest rate
        
        Returns
        -------
        :type terminal_amount: float 
            The monetary amount that can be obtained by selling the share at the end of the modelling window 
        """

        #return market_price / (terminal_rate - growth_rate)
        return market_price

    @tracer
    def generate_market_value(self, modelling_date: date, evaluated_date: date, market_price: float,
                              growth_rate: float) ->float:
        """
        Calculates the market value appreciation of an equity share between two points in time. 

        Parameters
        ----------
        self: EquityShare class
        :type modeling_date: date
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

        t = (evaluated_date - modelling_date).days / 365.5
        return market_price * (1 + growth_rate) ** t

    @tracer
    def generate_dividend_dates(self, modelling_date: date, end_date: date):
        """
        Generator yielding the dividend payment date starting from the first dividend
        paid after the modelling date. 

        Parameters
        ----------
        self: EquityShare class
        :type modelling_date: date
            The earliest date considered.
        :type end_date: date
            The latest date considered

        Returns
        -------
        :type yield float
            The date at which the dividend occurs
        """
        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.issue_date - delta
        while this_date < end_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date:  # Not interested in past payments
                continue
            if this_date <= end_date:
                yield this_date  # ? What is the advantage of yield here?

    def create_single_cash_flows(self, modelling_date: date, end_date: date, growth_rate: float)->dict:
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
        :type dividends: list of dict
            Dictionary of dictionaries containing the cash flow date and the size.        
        """

        dividend_amount = 0
        dividends = {}
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


    def create_single_terminal(self, modelling_date: date, end_date: date, terminal_rate: float, growth_rate: float)-> dict:
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
        :type terminal_rate: float
            Long term interest rate assumed by the run.      
        :type growth_rate: float
            Annualized growth rate of the equity of interest.
            
        Returns
        -------
        :type dividends: list of dict
            List of dictionaries containing the cash flow date and the size.        
        """

        terminals = {}
        market_price = self.generate_market_value(modelling_date, end_date, self.market_price,
                                                            growth_rate)
        terminal_amount = self.terminal_amount(market_price, growth_rate, terminal_rate)
        terminals.update({end_date: terminal_amount})
        return terminals

    def price_share(self, dividends: dict, terminal: dict, modelling_date: date, proj_period: int, curves: Curves)->float:
        date_frac = []
        cash_flow = []
        for key, value in dividends.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
            
        for key, value in terminal.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
        
        date_frac = pd.DataFrame(data = date_frac, columns = ["Date Fraction"]) # No need for Dataframes. Remove them
        cash_flow = pd.DataFrame(data = cash_flow, columns = ["Cash flow"])

        discount = curves.RetrieveRates(proj_period, date_frac.iloc[:, 0].to_numpy(), "Discount")

        nodisc_value = cash_flow.values*discount
        disc_value = sum(nodisc_value.values)
        return disc_value

    def bisection_growth(self, x_start: float, x_end:float, modelling_date:date, end_date:date, proj_period:int, curves: Curves, precision: float, max_iter:int)->float:
        """
        Bisection root finding algorithm for finding growth rate that when discounting with the risk free curve returns the market price.

        Args:
            self =           EquityShare object containing a single equity share positions
            x_start =        1 x 1 floating number representing the minimum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.05
            x_end =          1 x 1 floating number representing the maximum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.8
            modelling_date = 1 x 1 date, representing the date at which the entire run starts
            end_date =       1 x 1 date, representing the date at which the modelling window closes
            ufr  =           1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            proj_period  =   1 x 1 integer, representing the projection step at which the equity is calibrated. Ex. 1, 2
            curves =         Curves object containing data about the term structure
            precision =      1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            max_iter =       1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
            approx_function
        Returns:
            1 x 1 floating number representing the optimal growth of an equity to return the targeted market price 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> M_Obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_Obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> xStart = 0.05
            >>> xEnd = 0.5
            >>> maxIter = 1000
            >>> alfa = 0.15
            >>> ufr = 0.042
            >>> Precision = 0.0000000001
            >>> Tau = 0.0001
            >>> BisectionAlpha(xStart, xEnd, M_Obs, r_Obs, ufr, Tau, Precision, maxIter)
            [Out] 0.11549789285636511

        Implemented by Gregor Fabjan from Qnity Consultants on 08/02/2024.
        """
        terminal_rate = curves.ufr
        dividends = self.create_single_cash_flows(modelling_date, end_date, x_start)
        terminal = self.create_single_terminal(modelling_date, end_date, terminal_rate, x_start)
        y_start = self.price_share(dividends, terminal, modelling_date, proj_period, curves)[0]-self.market_price

        dividends = self.create_single_cash_flows(modelling_date, end_date, x_end)
        terminal = self.create_single_terminal(modelling_date, end_date, terminal_rate, x_end)
        y_end = self.price_share(dividends, terminal, modelling_date, proj_period, curves)[0]-self.market_price

        if np.abs(y_start) < precision:
            return x_start
        if np.abs(y_end) < precision:
            return x_end  # If final point already satisfies the conditions return end point
        i_iter = 0
        while i_iter <= max_iter:
            x_mid = (x_end + x_start) / 2  # calculate mid-point

            dividends = self.create_single_cash_flows(modelling_date, end_date, x_mid)
            terminal = self.create_single_terminal(modelling_date, end_date, terminal_rate, x_mid)
            y_mid = self.price_share(dividends, terminal, modelling_date, proj_period, curves)[0]-self.market_price
            if (y_mid == 0 or (x_end - x_start) / 2 < precision):  # Solution found
                return x_mid
            else:  # Solution not found
                i_iter += 1
                if np.sign(y_mid) == np.sign(
                        y_start):  # If the start point and the middle point have the same sign, then the root must be in the second half of the interval
                    x_start = x_mid
                else:  # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = x_mid
        return "Did not converge"


class EquitySharePortfolio():
    def __init__(self, equity_share: dict[int, EquityShare] = None):
        """
        Initialize the EquitySharePortfolio instance with the first EquityShare instance

        Parameters
        ----------        
        :type equity_share: dict[int,EquityShare]
        """
        logger.info("EquitySharePortfolio initializer called")
        self.equity_share = equity_share

    def IsEmpty(self) -> bool:
        if self.equity_share is None:
            return True
        if len(self.equity_share) == 0:
            return True
        return False

    def add(self, equity_share: EquityShare):
        """
        Add a new EquityShare to the EquitySharePortfolio instance

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated initial portfolio.
        :type equity_share: EquityShare
            The EquityShare instance representing a single equity instrument.

        """
        if self.equity_share is None:
            self.equity_share = {equity_share.asset_id: equity_share}
        else:
            self.equity_share.update({equity_share.asset_id: equity_share})

    def create_dividend_flows(self, modelling_date: date, end_date: date) -> list:
        """
        Create the list of dictionaries containing dates at which the dividends are paid out and the total amounts for
        all equity shares in the portfolio, for dates on or after the modelling date but not after the terminal date.

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
            A dictionary of dictionaries with datetime keys and cash-flow size values, containing all the dates at which the coupons are paid out.
        """
        all_dividends = {}
        equity_share: EquityShare
        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]  # Select one asset position
            dividends = equity_share.create_single_cash_flows(modelling_date, end_date, equity_share.growth_rate)
            all_dividends[asset_id] = dividends
        return all_dividends

    def create_terminal_flows(self, modelling_date: date, terminal_date: date, terminal_rate: float) -> dict:
        """
        Create the list of dictionaries containing dates at which the terminal cash-flows are paid out and the total amounts for
        all equity shares in the portfolio, for dates on or after the modelling date but not after the terminal date.

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the terminal dates and market values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).
        :type terminal_rate: float
            The assumed ultimate forward rate. The long term interest rate used in the Gordon growth model to calculate the terminal cash-flow

        Returns
        -------
        :rtype all_terminals
            A dictionary of dictionaries with datetime keys and cash-flow size values, containing all the dates at which the terminal cash-flows are paid out.
        """
        all_terminals = {}
        terminals: dict[date, float] = {}
        equity_share: EquityShare
        terminal_date: date

        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]
            terminals = equity_share.create_single_terminal(modelling_date, terminal_date, terminal_rate, equity_share.growth_rate)
            all_terminals[asset_id]=terminals
        return all_terminals

    def create_dividend_fractions(self, modelling_date: date, dividend_array: list) -> list:
        """
        Create the list of year-fractions at which each dividend is paid out (compared to the modelling date) and the list of
        relevant indices (aka. indices of cash flows that are within the modelling period)

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the dividend fraction is calculated.
        :type dividend_array: list of dictionaries
            Each element of the list represents a single equity asset. Each element contains a dictionary where has keys as dates at which the dividend cash flows are paid out
            and the values are the size of payment amount in local currency
            
        Returns
        -------
        :rtype dict Array with two elements: 
            all_dividend_date_frac: A list of numpy arrays, Each element in the list represents a sigle asset. Each numpy array represents the time fraction
            between the modelling date and the date of the cash flow (ex. 18 months from modelling date is 1.5).
            all_dividend_dates_considered: list of numpy arrays. Each element in the list represents a single asset. Each numpy array represents the indices of
            the cash flows from the dividend_array that mature within the period between the modelling date and the terminal date.
        """

        # other counting conventions MISSING
        # Remove numpy arrays in construction

        # Data structures list of lists for dividend payments
        all_date_frac = ([])  # this will save the date fractions of dividends for the portfolio
        all_dates_considered = (
            [])  # this will save if a cash flow is already expired before the modelling date in the portfolio

        for one_dividend_array in dividend_array:
            # equity_share = self.equity_share[asset_id]
            #            one_dividend_array = dividend_array[asset_id]

            # Reset objects for the next asset
            equity_date_frac = np.array([])  # this will save date fractions of dividends of a single asset
            equity_dates_considered = np.array(
                [])  # this will save the boolean, if the dividend date is after the modelling date

            dividend_counter = 0  # Counter of future dividend cash flows initialized to 0

            for one_dividend_date in list(one_dividend_array.keys()):  # for each dividend date of the selected equity
                one_dividend_days = (one_dividend_date - modelling_date).days
                if one_dividend_days > 0:  # dividend date is after the modelling date
                    equity_date_frac = np.append(
                        equity_date_frac, one_dividend_days / 365.25
                    )  # append date fraction
                    equity_dates_considered = np.append(
                        equity_dates_considered, int(dividend_counter)
                    )  # append "is after modelling date" flag
                dividend_counter += 1
                # else skip
            all_date_frac.append(
                equity_date_frac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            all_dates_considered.append(
                equity_dates_considered.astype(int)
            )  # append which cash flows are after the modelling date

        return [
            all_date_frac,
            all_dates_considered
        ]  # return all generated data structures (for now)

    def create_terminal_fractions(self, modelling_date: date, terminal_array: dict) -> dict:
        """
        Create the list of year-fractions at which the terminal amount is paid out (compared to the modelling date) and the list of
        relevant indices (aka. indices of cash flows that are within the modelling period)

        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type modelling_date: datetime.date
            The date from which the terminal fraction is calculated.
        :type terminal_array: list of dictionaries
            Each element of the list represents a single equity asset. Each element contains a dictionary where keys are the dates at which the terminal cash flow is paid out
            and the values are the size of payment in local currency
            
        Returns
        -------
        :rtype dict Array with two elements: 
            all_terminal_date_frac: A list of numpy arrays, Each element in the list represents a sigle asset. Each numpy array represents the time fraction
            between the modelling date and the terminal date (ex. 18 months from modelling date is 1.5).
            all_terminal_dates_considered: list of numpy arrays. Each element in the list represents a single asset. Each numpy array represents the index of
            the cash flow from the terminal_array that matures within the period between the modelling date and the terminal date.
        """

        # other counting conventions MISSING
        # Remove numpy arrays in construction

        # Data structures list of lists for dividend payments
        all_terminal_date_frac = ([])  # this will save the date fractions of dividends for the portfolio
        all_terminal_dates_considered = (
            [])  # this will save if a cash flow is already expired before the modelling date in the portfolio

        for one_terminal_array in terminal_array:

            # Reset objects for the next asset
            equity_terminal_date_frac = np.array([])  # this will save date fractions of dividends of a single asset
            equity_terminal_dates_considered = np.array(
                [])  # this will save the boolean, if the dividend date is after the modelling date

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
                equity_terminal_dates_considered.astype(int)
            )  # append which cash flows are after the modelling date

        return [
            all_terminal_date_frac,
            all_terminal_dates_considered
        ]

    def unique_dates_profile(self, cash_flow_profile: list):
        """
        Create a sorted list of dates at which there is an cash-flow event in any of the assets inside the portfolio and
        a single numpy array (matrix) representing those cash flows.


        Parameters
        ----------
        self: EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated portfolio.
        :type cashflow_profile: list of dictionaries containing the size and date of each 
            cash-flow for the equity portfolio


        :rtype dict list with two elements:
            unique_dates
            cash_flow_matrix
        """

        # define list of unique dates
        unique_dates = []
        for one_dividend_array in cash_flow_profile.values():
            for one_dividend_date in list(one_dividend_array.keys()):  # for each dividend date of the selected equity
                if one_dividend_date in unique_dates:  # If two cash flows on same date
                    pass
                    # Do nothing since dividend amounts are calibrated afterwards for equity
                    # dividends[dividend_date] = dividend_amount + dividends[dividend_date] # ? Why is here a plus? (you agregate coupon amounts if same date?)
                else:  # New cash flow date
                    unique_dates.append(one_dividend_date)

        return sorted(unique_dates)

    def cash_flow_profile_list_to_matrix(self, cash_flow_profile: list) -> list:

        unique_dates = self.unique_dates_profile(cash_flow_profile)
        width = len(unique_dates)
        height = len(cash_flow_profile)

        cash_flow_matrix = np.zeros((height, width))
        row = 0
        for one_cash_flow_array in cash_flow_profile:
            count = 0
            values = list(one_cash_flow_array.values())
            for one_cash_flow in one_cash_flow_array:
                column = unique_dates.index(one_cash_flow)
                cash_flow_matrix[row, column] = values[count]
                count += 1
            row += 1
        return [
            unique_dates,
            cash_flow_matrix]

    def init_equity_portfolio_to_dataframe(self, modelling_date: date)->list:

        asset_keys = self.equity_share.keys()

        market_price_tmp = []
        growth_rate_tmp = []
        asset_id_tmp = []
        units_tmp = []
        for key in asset_keys:
            market_price_tmp.append(self.equity_share[key].market_price)
            growth_rate_tmp.append(self.equity_share[key].growth_rate)
            asset_id_tmp.append(self.equity_share[key].asset_id)
            units_tmp.append(self.equity_share[key].units)

        market_price = pd.DataFrame(data=market_price_tmp, index=asset_id_tmp, columns=[modelling_date])

        growth_rate = pd.DataFrame(data=growth_rate_tmp, index=asset_id_tmp, columns=[modelling_date])
        
        units = pd.DataFrame(data=units_tmp, index=asset_id_tmp, columns=[modelling_date])

        return [market_price, growth_rate, units]

    # Calculate terminal value given growth rate, ultimate forward rate and vector of cash flows
    def equity_gordon(self, dividendyield, yieldrates, dividenddatefrac, ufr, g):

        num = np.power((1 + g), dividenddatefrac)
        den = np.power((1 + yieldrates), dividenddatefrac)
        termvalue = 1 / ((1 + yieldrates[-1]) ** dividenddatefrac[-1]) * 1 / (ufr - g)

        lhs = 1 / dividendyield
        return np.sum(num / den) + termvalue - lhs

    ## Bisection (To Update)
    def bisection_spread(x_start, x_end, dividendyield, r_obs_est, dividenddatefrac, ufr, Precision, maxIter,
                         growth_func):
        """
        Bisection root finding algorithm for finding the root of a function. The function here is the allowed difference between the ultimate forward rate and the extrapolated curve using Smith & Wilson.

        Args:
            cbPriced =  CorporateBondPriced object containing the list of priced bonds, spreads and cash flows
            x_start =    1 x 1 floating number representing the minimum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.05
            x_end =      1 x 1 floating number representing the maximum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.8
            M_Obs =     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u = [[1], [3]]
            r_Obs =     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            ufr  =      1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            Tau =       1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. Tau = 0.00001
            Precision = 1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            maxIter =   1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
            approx_function
        Returns:
            1 x 1 floating number representing the optimal value of the parameter alpha 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> M_Obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_Obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> xStart = 0.05
            >>> xEnd = 0.5
            >>> maxIter = 1000
            >>> alfa = 0.15
            >>> ufr = 0.042
            >>> Precision = 0.0000000001
            >>> Tau = 0.0001
            >>> BisectionAlpha(xStart, xEnd, M_Obs, r_Obs, ufr, Tau, Precision, maxIter)
            [Out] 0.11549789285636511

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf and https://en.wikipedia.org/wiki/Bisection_method
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """

        yStart = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr, x_start)
        yEnd = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr, x_end)
        if np.abs(yStart) < Precision:
            return x_start
        if np.abs(yEnd) < Precision:
            return x_end  # If final point already satisfies the conditions return end point
        iIter = 0
        while iIter <= maxIter:
            xMid = (x_end + x_start) / 2  # calculate mid-point
            yMid = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr,
                               xMid)  # What is the solution at midpoint
            if ((yStart) == 0 or (x_end - x_start) / 2 < Precision):  # Solution found
                return xMid
            else:  # Solution not found
                iIter += 1
                if np.sign(yMid) == np.sign(
                        yStart):  # If the start point and the middle point have the same sign, then the root must be in the second half of the interval
                    x_start = xMid
                else:  # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = xMid
        return "Did not converge"
