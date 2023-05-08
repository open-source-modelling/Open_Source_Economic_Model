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
        self.couponsize = []
        self.notionalsize = []

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
        startyear = self.issuedate.year
        endyear = self.maturitydate.year
        month =  self.issuedate.month
        day = self.issuedate.day
        # Missing what if date is 31,30
        # Missing other frequencies
        coupondate = np.array([]) 
        if self.frequency == 1:
            for selectedyear in range(startyear,endyear+1):
                coupondate = np.append(coupondate,dt.date(selectedyear,month,day))
        elif self.frequency == 2:
            #todo
            print("Not completed")
        else:
            #todo
            print("Not completed")
        
        # Notional payoff date is equal to maturity
        self.notionaldates = np.array([self.maturitydate])
        
        # Cash flow of each coupon
        couponsize = self.notional*self.couponrate
        self.couponcf = np.ones_like(coupondate)*couponsize
        
        # Cash flow of the principal payback
        self.notionalcf  = np.array([self.notional])
        self.coupondates = coupondate

class BondPrices:
    def __init__(self, modellingdate,zspread,compounding):
        self.modellingdate = modellingdate
        self.compounding = compounding
        self.marketprice = 0
        self.bookprice = 0
        self.zspread = zspread
        
    def refactordates(self,cfdate,modellingdate):
        # other counting conventions
        datenew = (cfdate-modellingdate)
        print(datenew)
        datefrac = np.array([])
        datesconsidered = np.array([])
        counter = 0
        for onedate in datenew:
            if onedate.days>0:
                datefrac = np.append(datefrac,onedate.days/365.25)
                datesconsidered = np.append(datesconsidered,int(counter))
            counter+=1

        return [datesconsidered.astype(int),datefrac]

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
        MV_CP = self.ratestodics(couponmaturities,couponrates,  self.compounding) * couponcf
        MV_NOT = self.ratestodics(notionalmaturities,notionalrates,  self.compounding) * notionalcf
        self.marketprice = sum(MV_CP)+ MV_NOT