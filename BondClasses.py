import numpy as np
import pandas as pd
from datetime import datetime as dt, timedelta
from datetime import date
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any
from FrequencyClass import Frequency
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

    def generate_coupon_dates(self, modelling_date: date, end_date) -> date:
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



class CorpBondPortfolio():
    def __init__(self, corporate_bonds: dict[int,CorpBond] = None):
        """
        Initialize the EquitySharePortfolio instance with the first EquityShare instance

        Parameters
        ----------        
        :type corporate_bonds: dict[int,CorpBond]
        """
        
        logger.info("CorpBondPortfolio initializer called")        
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
    
    def price_bond(self, coupons: dict, notional: dict, modelling_date: date, proj_period: int, curves, spread: float)->float:
        """
        To Do
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


class CorporateBond:
    def __init__(
        self,
        issuedate,
        maturitydate,
        frequency,
        notional,
        couponrate,
        recovrate,
        defprob,
        sspread,
        zspread,
        marketprice,
        compounding,
    ):
        self.issuedate = issuedate
        self.maturitydate = maturitydate
        self.frequency = frequency
        self.recovrate = recovrate
        self.couponrate = couponrate
        self.notional = notional
        self.defprob = defprob
        self.sspread = sspread
        self.zspread = zspread
        self.marketprice = marketprice
        self.coupondates = []
        self.notionaldates = []
        self.couponcfs = []
        self.notionalcfs = []
        self.notionaldatesfrac = []
        self.coupondatesfrac = []
        self.datesconsidered = []
        self.datesconsiderednot = []
        self.compounding = compounding

    def createcashflowdates(self):
        """
        Create the vector of dates at which the coupons and the principal are paid out.

        Needs numpy as np and datetime as dt

        Parameters
        ----------
        self : CorporateBond class instance
            The CorporateBond instance with populated initial portfolio.

        Returns
        -------
        CorporateBond.coupondates
            An array of datetimes, containing all the dates at which the coupons are paid out.
        CorporateBond.notionaldates
            An array of datetimes, containing the dates at which the principal is paid out
        """

        nAssets = self.issuedate.size

        for iBond in range(0, nAssets):
            issuedate = self.issuedate[iBond]
            enddate = self.maturitydate[iBond]

            dates = np.array([])
            thisdate = issuedate

            while thisdate <= enddate:  # Coupon payment dates
                if self.frequency[iBond] == 1:
                    thisdate = dt.date(thisdate.year + 1, thisdate.month, thisdate.day)
                    if thisdate <= enddate:
                        dates = np.append(dates, thisdate)
                    else:
                        # return dates
                        break
                elif self.frequency == 2:
                    thisdate = thisdate + dt.timedelta(days=182)
                    if thisdate <= enddate:
                        dates = np.append(dates, thisdate)
                    else:
                        break

            self.coupondates.append(dates)

            # Notional payoff date is equal to maturity
            self.notionaldates.append(np.array([self.maturitydate[iBond]]))

    def refactordates(self, MD):
        """
        Create the vector of dates at which the coupons and the principal are paid out.

        Needs numpy as np and datetime as dt

        Parameters
        ----------
        self : CorporateBond class instance
            The CorporateBond instance with populated initial portfolio and cash flow dates projected

        Returns
        -------
        CorporateBond.coupondatesfrac
            An array of date fractions, containing all the coupon date fractions at which the coupons are paid out compared to the modelling date.
        CorporateBond.datesconsidered
            An array of integers, containing the index of the coupon dates that are paid out after the modelling date.

        CorporateBond.notionaldatesfrac
            An array of date fractions, containing the date fractions at which the notional amount is paid out if the amount is after the modelling date
        CorporateBond.datesconsiderednot
            An array of integers , if the notional amount is paid after the modelling date and empty if not.
        """

        # other counting conventions MISSING

        nAssets = self.issuedate.size  # Number of assets in the bond portfolio

        # Data structures list of lists for coupon payments
        alldatefrac = (
            []
        )  # this will save the date fractions of coupons for the portfolio
        alldatesconsidered = (
            []
        )  # this will save if a cash flow is already expired before the modelling date in the portfolio

        # Data structure list of lists for notional amount repayment
        allnotionaldatefrac = (
            []
        )  # this will save the date fractions of notional amount repayment for the portfolio
        allnotionaldatesconsidered = (
            []
        )  # this will save if a bond is already expired before the modelling date in the portfolio

        for iAsset in range(0, nAssets):  # For each bond in the current portfolio
            # Reset objects for the next asset
            assetdatefrac = np.array(
                []
            )  # this will save date fractions of coupons of a single asset
            assetdatesconsidered = np.array(
                []
            )  # this will save the boolean, if the coupon date is after the modelling date

            assetnotionaldatefrac = np.array([])
            assetnotionaldatesconsidered = np.array(
                []
            )  # this will save the boolean, if the maturity date is after the modelling date

            couponcounter = 0  # Counter of future coupon cash flows initialized to 0

            datenew = (
                self.coupondates[iAsset] - MD
            )  # calculate the time difference between the coupondate and modelling date

            for onecoupondate in datenew:  # for each coupon date of the selected bond
                if onecoupondate.days > 0:  # coupon date is after the modelling date
                    assetdatefrac = np.append(
                        assetdatefrac, onecoupondate.days / 365.25
                    )  # append date fraction
                    assetdatesconsidered = np.append(
                        assetdatesconsidered, int(couponcounter)
                    )  # append "is after modelling date" flag
                couponcounter += 1
                # else skip
            alldatefrac.append(
                assetdatefrac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            alldatesconsidered.append(
                assetdatesconsidered.astype(int)
            )  # append which cash flows are after the modelling date

            # Calculate if the maturity date is before the modelling date
            assetcalcnotionaldatefrac = (
                self.notionaldates[iAsset] - MD
            )  # calculate the time difference between the maturity date and modelling date

            if (
                assetcalcnotionaldatefrac[0].days > 0
            ):  # if maturity date is after modelling date
                assetnotionaldatefrac = np.append(
                    assetnotionaldatefrac, assetcalcnotionaldatefrac[0].days / 365.25
                )  # append date fraction
                assetnotionaldatesconsidered = np.append(
                    assetnotionaldatesconsidered, int(1)
                )  # append "is after modelling date" flag
            # else skip
            allnotionaldatefrac.append(
                assetnotionaldatefrac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            allnotionaldatesconsidered.append(
                assetnotionaldatesconsidered.astype(int)
            )  # append which cash flows are after the modelling date

        # Save coupon related data structures into the object
        self.coupondatesfrac = alldatefrac
        self.datesconsidered = alldatesconsidered

        # Save notional amount related data structures into the object
        self.notionaldatesfrac = allnotionaldatefrac
        self.datesconsiderednot = allnotionaldatesconsidered

        return [
            alldatefrac,
            alldatesconsidered,
            allnotionaldatefrac,
            allnotionaldatesconsidered,
        ]  # return all generated data structures (for now)

    def createcashflowsnew(self):
        """
        Convert information about the zero coupon bonds into a series of cash flows and a series of dates at which the cash flows are paid.

        Needs numpy as np
        Parameters
        ----------
        self : CorporateBond class instance
            The CorporateBond instance with populated initial portfolio, cash flow dates projected and the modelling date selected

        Returns
        -------
        numpy.ndarray
            An array of rates calculated using the specified compounding frequency.

            #STILL TO COVERT INTO CASHFLOW AND NOTIONAL ONLY FOR CONSIDERED CASH FLOWS
        """
        nAssets = self.issuedate.size

        # Missing what if date is 31,30
        # Missing other frequencies

        # Data structures list of lists for coupon payments
        allcashflows = (
            []
        )  # this will save the date fractions of coupons for the portfolio

        # Data structure list of lists for notional amount repayment
        allnotionalcashflows = (
            []
        )  # this will save the date fractions of notional amount repayment for the portfolio

        # Cash flow of each coupon
        couponsize = self.notional * self.couponrate

        for iBond in range(0, nAssets):
            # Reset objects for the next asset
            assetcashflows = np.array(
                []
            )  # this will save date fractions of coupons of a single asset
            assetnotionalcashflows = np.array([])

            for coupon in self.coupondatesfrac[iBond]:
                assetcashflows = np.append(
                    assetcashflows, couponsize[iBond]
                )  # append date fraction

            allcashflows.append(assetcashflows)

            assetnotionalcashflows = np.append(
                assetnotionalcashflows, self.notional[iBond]
            )  # append date fraction

            allnotionalcashflows.append(assetnotionalcashflows)
        self.couponcfs = allcashflows
        self.notionalcfs = allnotionalcashflows
        return [allcashflows, allnotionalcashflows]


    def disctorates(self, disc, timefrac, compounding):
        """
        Convert discount factors to continuously compounded rates or rates compounded annually.

        Needs numpy as np
        Parameters
        ----------
        Disc : numpy.ndarray
            An array of discount factors.
        Ttime : numpy.ndarray
            An array of time differences between the start and end of each period.
        Compounding : int
            Compounding frequency. Set to -1 for continuous compounding, 0 for simple compounding and
            n (positive integer) for n times per year compounding.

        Returns
        -------
        numpy.ndarray
            An array of rates calculated using the specified compounding frequency.

        """

        # Case where a time is devided by zero error
        disc[timefrac == 0] = 1
        timefrac[timefrac == 0] = 1

        if compounding == -1:  # Continious time convention
            rates = -np.log(disc) / timefrac
        elif compounding == 0:
            rates = (disc - 1) / timefrac
        else:
            rates = (disc ** (-1 / (timefrac * compounding)) - 1) * compounding

        return rates

    def ratestodics(self, rates, timefrac, compounding):
        """
        Converts discount rates to discount factors using a selected compounding convention.

        Needs numpy as np
        Parameters
        ----------
        rates : numpy.ndarray
            An array of discount rates.
        ttime : numpy.ndarray
            An array of time differences between the start and end of each period.
        compounding : int
            Compounding frequency. Set to -1 for continuous compounding, 0 for simple compounding and
            n (positive integer) for n times per year compounding.

        Returns
        -------
        numpy.ndarray
            An array of discount factors calculated using the specified compounding frequency.

        """
        if compounding == -1:  # Continious time convention
            disc = np.exp(-rates * timefrac)
        elif compounding == 0:
            disc = (1 + rates * timefrac) ** (-1)
        else:
            disc = (1 + rates / compounding) ** (-timefrac * compounding)

        return disc

    def PriceBond(
        self,
        couponrates,
        notionalrates,
        couponmaturities,
        notionalmaturities,
        couponcf,
        notionalcf,
        sSpread,
        zSpread,
    ):
        nAsset = len(couponrates)
        self.marketprice = []

        for iAsset in range(0, nAsset):
            # Add to skip if empty
            MV_CP = (
                self.ratestodics(
                    couponmaturities[iAsset],
                    couponrates[iAsset] + sSpread[iAsset] + zSpread[iAsset],
                    self.compounding,
                )
                * couponcf[iAsset]
            )
            MV_NOT = (
                self.ratestodics(
                    notionalmaturities[iAsset],
                    notionalrates[iAsset] + sSpread[iAsset] + zSpread[iAsset],
                    self.compounding,
                )
                * notionalcf[iAsset]
            )
            MV = np.sum(MV_CP) + MV_NOT
            self.marketprice.append(np.array(MV))

    def OpenPriceBond(
        self,
        couponrates,
        notionalrates,
        couponmaturities,
        notionalmaturities,
        couponcf,
        notionalcf,
        sSpread,
        zSpread,
    ):
        MV_CP = (
            self.ratestodics(
                couponmaturities, couponrates + sSpread + zSpread, self.compounding
            )
            * couponcf
        )
        MV_NOT = (
            self.ratestodics(
                notionalmaturities, notionalrates + sSpread + zSpread, self.compounding
            )
            * notionalcf
        )
        MV = np.sum(MV_CP) + MV_NOT

        return MV
