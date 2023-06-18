import numpy as np
import datetime as dt

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
