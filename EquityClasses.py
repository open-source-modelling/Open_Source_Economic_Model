import numpy as np
import datetime as dt

class Equity:
    def __init__(self, nace, issuedate, issuername, dividendyield, frequency, marketprice):
        self.nace = nace
        self.issuedate = issuedate
        self.issuername = issuername 
        self.dividendyield = dividendyield 
        self.frequency = frequency
        self.marketprice = marketprice 
        self.growthrate = []
        self.terminalvalue = []
        self.dividenddates = []
        self.terminaldates =[]
        self.dividendcfs = []
        self.terminalcfs = []

class EquityPriced:
    def __init__(self, modellingdate,compounding, enddate):
        self.modellingdate = modellingdate
        self.compounding = compounding
        self.enddate = enddate
        self.marketprice = []
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
        
        # Cash flow of each coupon
        couponsize = self.notional*self.couponrate

        self.couponcfs = []
        self.coupondates = []
        self.notionaldates = []
        self.notionalcfs = []
        for iBond in range(0,nAssets):
            startyear = self.issuedate[iBond].year
            endyear   = self.maturitydate[iBond].year
            month     = self.issuedate[iBond].month
            day       = self.issuedate[iBond].day
            
            coupondateone = np.array([])
            
            if self.frequency[iBond] == 1:
                for selectedyear in range(startyear,endyear+1): # Creates array of dates for selected ZCB
                    coupondateone = np.append(coupondateone,dt.date(selectedyear,month,day))
            elif self.frequency[iBond] == 2:
                #todo
                print("Not completed")
            else:
                #todo
                print("Not completed")
            
            self.couponcfs.append(np.ones_like(coupondateone)*couponsize[iBond])
            self.coupondates.append(coupondateone)

            # Notional payoff date is equal to maturity
            self.notionaldates.append(np.array([self.maturitydate[iBond]]))
       
            # Cash flow of the principal payback
            self.notionalcfs.append(np.array(self.notional[iBond]))
