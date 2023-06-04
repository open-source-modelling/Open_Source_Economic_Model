import numpy as np
import datetime as dt

class Equity:
    def __init__(self, nace, issuedate, issuername, dividendyield, frequency, marketprice,terminalvalue):
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
        self.growthrate = []
        self.dividenddates = []
        self.dividendfrac = []
        self.terminaldates =[]
        self.dividendcfs = []
        self.terminalcfs = []

class EquityPriced:
    def __init__(self, modellingdate,compounding, enddate, dividendyield, marketprice, terminalvalue):
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
        self.growthrate = []
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
        # Produce array of dates when coupons are paid out
       
        nAssets = self.issuedate.size
        
        # Missing what if date is 31,30
        # Missing other frequencies
        
        # Cash flow of each dividend
        dividendsize = self.marketprice*self.dividendyield

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
