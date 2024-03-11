import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from datetime import date
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any
from FrequencyClass import Frequency
from CurvesClass import Curves
import logging


logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(("%(levelname)s:%(name)s:%(mesage)s"))

file_handler = logging.FileHandler("BondClass.log")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

@dataclass(frozen=True)
class CorpBond:
    asset_id: int
    nace: str
    issuer: str
    issue_date: date
    maturity_date: date
    coupon_rate: float
    notional_amount: float
    zspread: float
    frequency: Frequency
    recovery_rate: float
    default_probability: float
    units: float
    market_price: float

    def __post_init__(self) -> None:
        if self.asset_id<=0:
            raise ValueError("Asset ID must be greater than 0")
        if self.coupon_rate < 0:
            raise ValueError("Coupon rate cannot be negative")
        if self.coupon_rate > 1:
            raise ValueError("Coupon rate cannot be greater than 1")
        if self.recovery_rate < 0:
            raise ValueError("Recovery rate cannot be negative")
        if self.recovery_rate > 1:
            raise ValueError("Recovery rate cannot be greater than 1")
        if self.default_probability < 0:
            raise ValueError("Default probability cannot be negative")
        if self.default_probability > 1:
            raise ValueError("Default probability cannot be greater than 1")
        if self.market_price < 0:
            raise ValueError("Market price cannot be negative")
        if self.frequency not in [Frequency.MONTHLY, Frequency.QUARTERLY,Frequency.TRIANNUAL, Frequency.BIANNUAL, Frequency.ANNUAL]:
            raise ValueError("Frequency must be either Monthly, Quarterly,Triannual, SemiAnnual or Annual")
        if self.notional_amount <= 0:
            raise ValueError("Notional amount must be greater than 0")
        if self.maturity_date <= self.issue_date:
            raise ValueError("Maturity date cannot be before issue date")



    def coupon_amount(self) -> float:
        """
        Calculate the size of the coupon for a bond inside the CorpBond class.
        The coupon amount is equal to the percentage of the notional value.
        
        Parameters
        ----------
        self: CorpBond class
        
        Returns
        -------
        :rtype float 
            The monetary amount of the coupon
        """
        coupon = self.coupon_rate * self.notional_amount
        return coupon

    def generate_coupon_dates(self, modelling_date: date, end_date: date) -> date:
        """
        Generator yielding the coupon payment date starting from the first coupon
        paid after the modelling date. 

        Parameters
        ----------
        self: CorpBond class
        :type modelling_date: date
            The earliest date considered.
        :type end_date: date
            The latest date considered

        Returns
        -------
        :type yield float
            The date at which the coupon payment occurs
        """

        end_date = min(end_date, self.maturity_date)

        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.issue_date - delta
        while this_date < self.maturity_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date: #Not interested in past payments
                continue
            if this_date <= self.maturity_date:
                yield this_date


    def create_single_cash_flows(self, modelling_date: date, end_date: date)->dict:
        """
        Create a dictionary of coupon cash flows using information about a corporate bond. The 
        return dictionary has dates of the cash flows as keys and monetary amounts as values. 
        
        Parameters
        ----------
        self: CorpBond instance
            The CorpBond instance with the bond position of interest.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).
            
        Returns
        -------
        :type dividends: list of dict
            Dictionary of dictionaries containing the cash flow date and the size.        
        """

        coupon_size = 0
        coupons = {}
        for coupon_date in self.generate_coupon_dates(modelling_date, end_date):
            if coupon_date in coupons:  # If two cash flows on same date
                pass
                # dividends[dividend_date] = dividend_amount + dividends[dividend_date]
            else:  # New cash flow date
                coupon_size = self.coupon_amount()
                coupons.update({coupon_date: coupon_size})
        return coupons
    

    def create_single_maturity(self, end_date: date)-> dict:
        """
        Create a dictionary of terminal cash flows using information about a bond portfolio. The 
        return dictionary has dates of the cash flows as keys and monetary amounts as values. 
        
        Parameters
        ----------
        self: CorpBond instance
            The CorpBond instance with the bond position of interest.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).
            
        Returns
        -------
        :type dividends: list of dict
            List of dictionaries containing the cash flow date and the size.        
        """
        
        principals = {}
        terminal_amount = self.notional_amount
        terminal_date = min(end_date, self.maturity_date)
        principals.update({terminal_date: terminal_amount})
        return principals    

    def term_to_maturity(self, modelling_date: date)->int:
        """
        Calculates the number of days between the modelling date and the redemption date of the bond

        Parameters
        ----------
        :parameter modelling_date
        :type date
        The modelling start date


        :returns int
        The number of days between the modelling date and the redemption date of the bond
        """
        delta: timedelta = self.maturity_date - modelling_date
        return delta.days

    def gross_redemption_yield(self):
        pass

    def price_bond(self, coupons: dict, notional: dict, modelling_date: date, proj_period: int, curves, spread: float)->float:
        """
        Calculate the price of a bond with defined coupon and notional payments using the 
        yield curve obtained from the curves object with a fixed extra spread passed in spread.  

        Parameters
        ----------
        self: CorpBond instance
            The CorpBond instance with the bond position of interest.
        :type coupons: dict
            A dictionary with dates of coupon cashflows as keys and monetary amounts as values.
        :type notional: dict
            A dictionary with dates of repayments of the notional as keys and monetary amounts as values.              
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type proj_period: int
            Which modelling date in dates of interest is the pricing function using.
        :type curves: Curves
            Instance of the Curves class with calibrated term structure.
        :type spread: float
            Extra spread over the risk free rate applied to the bond.
        

        Returns
        -------
        :type disc_value: float
            The price of the bond.         
        """

        date_frac = []
        cash_flow = []
        
        for key, value in coupons.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
            
        for key, value in notional.items():
            date_tmp = (key-modelling_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)
        
        date_frac = pd.DataFrame(data = date_frac, columns = ["Date Fraction"]) # No need for Dataframes. Remove them
        cash_flow = pd.DataFrame(data = cash_flow, columns = ["Cash flow"])

        discount = curves.RetrieveRates(proj_period, date_frac.iloc[:, 0].to_numpy(), "Discount", spread)

        nodisc_value = cash_flow.values*discount
        disc_value = sum(nodisc_value.values)
        return disc_value

    def bisection_spread(self, x_start: float, x_end:float, modelling_date:date, end_date:date, proj_period:int, curves: Curves, precision: float, max_iter:int)->float:
        """
        Bisection root finding algorithm for finding the spread that when discounting with the risk free curve returns the market price.

        Args:
            self =           EquityShare object containing a single equity share positions
            x_start =        1 x 1 floating number representing the minimum allowed value of the spread. Ex. spread = 0.05
            x_end =          1 x 1 floating number representing the maximum allowed value of the spread. Ex. spread = 0.8
            modelling_date = 1 x 1 date, representing the date at which the entire run starts
            end_date =       1 x 1 date, representing the date at which the modelling window closes
            proj_period  =   1 x 1 integer, representing the projection step at which the equity is calibrated. Ex. 1, 2
            curves =         Curves object containing data about the term structure
            precision =      1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            max_iter =       1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
            approx_function
        Returns:
            1 x 1 floating number representing the spread of the corporate bond implied by the market price and the yield curve dynamics 

        Implemented by Gregor Fabjan from Qnity Consultants on 09/02/2024.
        """

        dividends = self.create_single_cash_flows(modelling_date, end_date)
        terminal = self.create_single_maturity(end_date)
        y_start = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_start)[0]-self.market_price

        dividends = self.create_single_cash_flows(modelling_date, end_date)
        terminal = self.create_single_maturity(end_date)
        y_end = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_end)[0]-self.market_price

        if np.abs(y_start) < precision:
            return x_start
        if np.abs(y_end) < precision:
            return x_end  # If final point already satisfies the conditions return end point
        i_iter = 0
        while i_iter <= max_iter:
            x_mid = (x_end + x_start) / 2  # calculate mid-point

            dividends = self.create_single_cash_flows(modelling_date, end_date)
            terminal = self.create_single_maturity(end_date)
            y_mid = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_mid)[0]-self.market_price
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


class CorpBondPortfolio():
    def __init__(self, corporate_bonds: dict[int,CorpBond] = None):
        """
        Initialize the EquitySharePortfolio instance with the first EquityShare instance

        Parameters
        ----------        
        :type corporate_bonds: dict[int,CorpBond]
        """
        
        #logger.info("CorpBondPortfolio initializer called")        
        self.corporate_bonds = corporate_bonds

    def IsEmpty(self)-> bool:
        if self.corporate_bonds is None:
            return True
        if len(self.corporate_bonds) == 0:
            return True
        return False

    def add(self,corp_bond: CorpBond) :
        """

        :type corp_bond: CorpBond
        """
        if self.corporate_bonds is not None:
            self.corporate_bonds.update({corp_bond.asset_id: corp_bond})
        else:
            self.corporate_bonds = {corp_bond.asset_id: corp_bond}

    def create_aggregate_coupon_dates(self, modelling_date)->dict:
        """
                Create the vector of dates at which the coupons are paid out and the total amounts for
                all corporate bonds in the portfolio, for dates on or after the modelling date

                Parameters
                ----------
                self : CorpBondPortfolio class instance
                    The CorpBondPortfolio instance with populated initial portfolio.

                Returns
                -------
                CorporateBond.coupondates
                    An array of datetimes, containing all the dates at which the coupons are paid out.

                """

        coupons: dict[date, float] = {}
        corp_bond: CorpBond
        coupon_date: date
        for asset_id in self.corporate_bonds:
            corp_bond = self.corporate_bonds[asset_id]
            for coupon_date in corp_bond.generate_coupon_dates(modelling_date):
                if coupon_date in coupons:
                    coupons[coupon_date] += corp_bond.coupon_amount()
                else:
                    coupons.update({coupon_date:corp_bond.coupon_amount()})
        return coupons

    def create_coupon_flows(self, modelling_date: date, end_date: date) -> list:
        """
        Create the list of dictionaries containing dates at which the coupons are paid out and the total amounts for
        all corporate bonds in the portfolio, for dates on or after the modelling date but not after the terminal date.

        Parameters
        ----------
        self: CorpBondPortfolio class instance
            The CorpBondPortfolio instance with populated initial portfolio.
        :type modelling_date: datetime.date
            The date from which the dividend dates and values start.
        :type end_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        :rtype all_coupons
            A dictionary of dictionaries with datetime keys and cash-flow size values, containing all the dates at which the coupons are paid out.
        """
        all_coupons = {}
        corporate_bond: CorpBond
        for asset_id in self.corporate_bonds:
            corporate_bond = self.corporate_bonds[asset_id]  # Select one asset position
            coupons = corporate_bond.create_single_cash_flows(modelling_date, end_date)
            all_coupons[asset_id] = coupons
        return all_coupons 

    def create_maturity_flows(self, terminal_date: date) -> dict:
        """
        Create the list of dictionaries containing dates at which each bond matures and its notional is paid out. If the maturity is after the 
        end of the modelling window, the bond returns the notional at the end of the modelling window.

        Parameters
        ----------
        self: CorpBondPortfolio class instance
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
        all_maturity = {}
        principals: dict[date, float] = {}
        corp_bond: CorpBond
        terminal_date: date

        for asset_id in self.corporate_bonds:
            corp_bond = self.corporate_bonds[asset_id]
            principals = corp_bond.create_single_maturity(terminal_date)
            all_maturity[asset_id]=principals
        return all_maturity
    

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

    def init_bond_portfolio_to_dataframe(self, modelling_date: date)->list:

        asset_keys = self.corporate_bonds.keys()

        market_price_tmp = []
        zspread_tmp = []
        asset_id_tmp = []
        units_tmp = []
        for key in asset_keys:
            market_price_tmp.append(self.corporate_bonds[key].market_price)
            zspread_tmp.append(self.corporate_bonds[key].zspread)
            asset_id_tmp.append(self.corporate_bonds[key].asset_id)
            units_tmp.append(self.corporate_bonds[key].units)

        market_price = pd.DataFrame(data=market_price_tmp, index=asset_id_tmp, columns=[modelling_date])

        zspread = pd.DataFrame(data=zspread_tmp, index=asset_id_tmp, columns=[modelling_date])
        
        units = pd.DataFrame(data=units_tmp, index=asset_id_tmp, columns=[modelling_date])

        return [market_price, zspread, units]


    """
    def create_coupon_dates(self, modelling_date: date):
        for corp_bond in self.corporate_bonds.values() :
            corp_bond.generate_coupon_dates(modelling_date)
    """


    def create_maturity_cashflow(self, modelling_date: date) -> dict:
        """

        :rtype: dict
        """
        maturities: dict[date, float] = {}
        corp_bond: CorpBond
        maturity_date: date

        for asset_id in self.corporate_bonds:
            corp_bond = self.corporate_bonds[asset_id]
            if maturity_date in maturities:
                maturities[maturity_date] += corp_bond.notional_amount
            else:
                maturities.update({corp_bond.maturity_date:corp_bond.notional_amount})
        return maturities