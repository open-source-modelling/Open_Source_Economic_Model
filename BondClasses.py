import numpy as np
import datetime as dt

class ZeroCouponBond:
    def __init__(self,issuedate, maturitydate, frequency, notional, couponrate, recovrate, defprob, zspread):
        self.issuedate = issuedate
        self.maturitydate = maturitydate
        self.frequency = frequency
        self.recovrate = recovrate
        self.couponrate = couponrate
        self.notional = notional
        self.defprob = defprob
        self.zspread = zspread
        self.coupondates = []
        self.notionaldates =[]
        self.couponcfs = []
        self.notionalcfs = []

    def createcashflows(self):
        """
        Convert information about the zero coupon bonds into a series of cash flows and a series of dates at which the cash flows are paid.

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

class ZeroCouponBondPriced:
    def __init__(self, modellingdate,zspread,compounding):
        self.modellingdate = modellingdate
        self.compounding = compounding
        self.marketprice = 0
        self.bookprice = 0
        self.zspread = zspread
        self.coupondatefrac = []
        self.notionaldatefrac =[]
        self.couponcfs = []
        self.notionalcfs = []



        
    def refactordates(self,cfdate,modellingdate):
        # other counting conventions
        nAsset = len(cfdate)
        datefracout = []
        datesconsideredout = []
        for iAsset in range(0,nAsset):
            datenew = (cfdate[iAsset]-modellingdate)
            datefrac = np.array([])
            datesconsidered = np.array([])
            counter = 0
            for onedate in datenew:
                if onedate.days>0:
                    datefrac = np.append(datefrac,onedate.days/365.25)
                    datesconsidered = np.append(datesconsidered,int(counter))
                counter+=1

            datefracout.append(datefrac)
            datesconsideredout.append(datesconsidered.astype(int))
            
        return [datesconsideredout,datefracout]

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

        if compounding == -1: # Continious time convention
            rates = -np.log(disc) / timefrac
        elif compounding == 0: 
            rates = (disc - 1) / timefrac
        else:
            rates = (disc ** (-1 / (timefrac * compounding)) - 1) * compounding

        return rates


    def ratestodics(self, rates,timefrac,compounding):
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
        if compounding == -1: # Continious time convention
            disc = np.exp(-rates * timefrac)
        elif compounding == 0: 
            disc = (1 + rates * timefrac)**(-1)
        else:
            disc = (1+ rates/compounding) ** (-timefrac*compounding)

        return disc   

    def PriceBond(self, couponrates,notionalrates,couponmaturities, notionalmaturities,couponcf,notionalcf):
        nAsset = len(couponrates)
        self.marketprice = []

        for iAsset in range(0,nAsset):
            MV_CP = self.ratestodics(couponmaturities[iAsset],couponrates[iAsset], self.compounding) * couponcf[iAsset]
            MV_NOT = self.ratestodics(notionalmaturities[iAsset],notionalrates[iAsset],  self.compounding) * notionalcf[iAsset]
            MV = np.sum(MV_CP)+MV_NOT
            self.marketprice.append(np.array(MV))
            #self.marketprice.append(np.sum(np.sum(MV_CP,MV_NOT)))