import numpy as np
from datetime import datetime as dt, timedelta
from datetime import date
from enum import IntEnum
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any


class Frequency(IntEnum):
    ANNUAL = 1
    BIANNUAL = 2
    TRIANNUAL = 3
    QUARTERLY = 4
    MONTHLY = 12


@dataclass
class EquityShare:
    asset_id: int
    nace: str
    issuer: str
    buy_date: date
    dividend_yield: float
    frequency: Frequency
    market_price: float

    @property
    def dividend_amount(self) -> float:
        return self.dividend_yield # Probably needs to be removed

    def generate_dividend_dates(self, modelling_date: date, end_date: date ) -> date:
        """

        :type modelling_date: date
        """
        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.buy_date - delta
        while this_date < end_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date: #Not interested in past payments
                continue
            if this_date <= end_date:
                yield this_date # ? What is the advantage of yield here?

class EquitySharePortfolio():
    def __init__(self, equity_share: dict[int,EquityShare] = None):
        """

        :type equity_share: dict[int,EquityShare]
        """
        self.equity_share = equity_share

    def IsEmpty(self)-> bool:
        if self.equity_share == None:
            return True
        if len(self.equity_share) == 0:
            return True
        return False

    def add(self,equity_share: EquityShare) :
        """

        :type equity_share: EquityShare
        """
        if self.equity_share == None:
            self.equity_share = {equity_share.asset_id: equity_share}
        else:
            self.equity_share.update({equity_share.asset_id: equity_share})



    def create_dividend_dates(self, modelling_date, end_date)->dict:
        """
                Create the vector of dates at which the dividends are paid out and the total amounts for
                all equity shares in the portfolio, for dates on or after the modelling date

                Parameters
                ----------
                self : EquitySharePortfolio class instance
                    The EquitySharePortfolio instance with populated initial portfolio.

                Returns
                -------
                EquityShare.coupondates
                    An array of datetimes, containing all the dates at which the coupons are paid out.

                """

        dividends: dict[date, float] = {}
        equity_share: EquityShare
        dividend_date: date
        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]
            dividend_amount = equity_share.dividend_amount
            for dividend_date in equity_share.generate_dividend_dates(modelling_date, end_date):
                if dividend_date in dividends:
                    dividends[dividend_date] = dividend_amount + dividends[dividend_date] # ? Why is here a plus? (you agregate coupon amounts if same date?)
                else:
                    dividends.update({dividend_date:dividend_amount})
        return dividends

# Missing create cash flows





class Equity:
    def __init__(self, nace, issuedate, issuername, dividendyield, frequency, marketprice,terminalvalue,enddate):
        """
        Equity class saves 
        
        Properties
        ----------
        nace
        issuedate        
        frequency
        marketprice
        dividendyield
        terminalvalue
        growthrate
        dividenddates
        dividendfrac
        terminaldates
        dividendcfs
        terminalcfs        

        """
        self.nace = nace
        self.issuedate = issuedate
        self.issuername = issuername
        self.frequency = frequency
        self.marketprice = marketprice
        self.dividendyield = dividendyield
        self.terminalvalue = terminalvalue
        self.enddate = enddate
        self.terminaldates = []
        self.growthrate = []
        self.dividenddates = []
        self.dividendfrac = []
        self.terminaldates =[]
        self.dividendcfs = []
        self.terminalcfs = []

    def createcashflowdates(self):
        """
        Create the vector of dates at which the dividends and terminal value are paid out.

        Needs numpy as np and datetime as dt
        
        Parameters
        ----------
        self : CorporateBond class instance
            The CorporateBond instance with populated initial portfolio.

        Returns
        -------
        Equity.dividenddates
            An array of datetimes, containing all the dates at which the coupons are paid out.
        Equity.terminaldates
            An array of datetimes, containing the dates at which the principal is paid out
        """       

        nAssets = self.issuedate.size

        for iEquity in range(0,nAssets):
            issuedate = self.issuedate[iEquity]
            enddate   = self.enddate[iEquity]

            dates = np.array([])
            thisdate = issuedate

            while thisdate <= enddate:
                if self.frequency == 1:
                    thisdate = dt.date(thisdate.year + 1, thisdate.month, thisdate.day)
                    if thisdate <=enddate:
                        dates = np.append(dates,thisdate)
                    else:
                        #return dates
                        break
                elif self.frequency == 2:
                    thisdate = thisdate + dt.timedelta(days=182)
                    if thisdate <= enddate:
                        dates = np.append(dates, thisdate)
                    else:
                        break                

            self.dividenddates.append(dates)

            # Notional payoff date is equal to maturity
            self.terminaldates.append(np.array([self.enddate[iEquity]]))


class EquityPriced:
    def __init__(self, modellingdate,compounding, enddate, dividendyield, marketprice, terminalvalue, growthrates):
        """
        Equity class saves 
        
        Properties
        ----------
        modellingdate
        compounding
        enddate
        dividendyield
        growthrate
        marketprice
        terminalvalue
        bookprice
        dividenddatefrac
        terminaldatefrac
        dividendcfs
        terminalcfs
        """

        self.modellingdate = modellingdate
        self.compounding = compounding
        self.enddate = enddate
        self.dividendyield = dividendyield 
        self.growthrate = growthrates
        self.marketprice = marketprice 
        self.terminalvalue = terminalvalue
        self.bookprice = []
        self.dividenddatefrac = []
        self.terminaldatefrac =[]
        self.dividendcfs = []
        self.terminalcfs = []

  
    def createcashflows(self):
        """
        Convert information about the equity into a series of cash flows and a series of dates at which the cash flows are paid.

        Needs numpy as np
        Parameters
        ----------
        self : EquityPriced object
            

        Modifies
        -------
        EquityPriced
            ToDo.

        """       
        # Produce array of dates when coupons are paid out
       
        nAssets = self.marketprice.size
        
        # Missing what if date is 31,30
        # Missing other frequencies
        
        # Cash flow of each dividend
        #dividendsize = self.marketprice*self.dividendyield

        self.dividendcfs = []
        self.dividenddates = []
        self.terminaldates = []
        self.terminalcfs = []

        for iEquity in range(0,nAssets):
            startyear = self.issuedate[iEquity].year
            endyear   = self.maturitydate[iEquity].year
            month     = self.issuedate[iEquity].month
            day       = self.issuedate[iEquity].day
            
            coupondateone = np.array([])
            
            if self.frequency[iEquity] == 1:
                for selectedyear in range(startyear,endyear+1): # Creates array of dates for selected ZCB
                    dividenddateone = np.append(dividenddateone,dt.date(selectedyear,month,day))
            elif self.frequency[iEquity] == 2:
                #todo
                print("Not completed")
            else:
                #todo
                print("Not completed")
            
            self.dividendcfs.append(np.ones_like(dividenddateone)*dividendsize[iEquity])
            self.dividenddates.append(dividenddateone)

            # Terminal payoff date is equal to maturity
            self.terminaldates.append(np.array([self.maturitydate[iEquity]]))
       
            # Cash flow of the principal payback
            self.terminalcfs.append(np.array(self.terminal[iEquity]))
