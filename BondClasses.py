import numpy as np
import datetime as dt

class CorporateBond:
    def __init__(self,issuedate, maturitydate, frequency, notional, couponrate, recovrate, defprob, sspread, zspread,marketprice):
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
        self.notionaldates =[]
        self.couponcfs = []
        self.notionalcfs = []


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

        for iBond in range(0,nAssets):
            
            issuedate = self.issuedate[iBond]
            enddate   = self.maturitydate[iBond]

            dates = np.array([])
            thisdate = issuedate

            while thisdate <= enddate: # Coupon payment dates
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

            self.coupondates.append(dates)
            
            # Notional payoff date is equal to maturity
            self.notionaldates.append(np.array([self.maturitydate[iBond]]))

    def refactordates(self, MD):
        # other counting conventions MISSING
        
        nAssets = self.issuedate.size # Number of assets in the bond portfolio
    
        datefracout = np.array([]) # this will save the date fractions of coupons for the portfolio
        datesconsideredout = np.array([]) # this will save if a bond is already expired before the modelling date in the portfolio
        
        for iAsset in range(0,nAssets):
            datenew = (self.coupondates[iAsset]-MD) # calculate the time difference between the coupondate and modelling date
            datefrac = np.array([]) # this will save date fractions of coupons of a single asset
            datesconsidered = np.array([]) # this will save the boolean, if the coupon date is after the modelling date
            counter = 0
            for onedate in datenew: # for each coupon date
                
                if onedate.days>0: # coupon date is after the modelling date
                    datefrac = np.append(datefrac,onedate.days/365.25) # append date fraction
                    datesconsidered = np.append(datesconsidered,int(counter)) # append "is after modelling date" flag
                counter+=1
                # else skip


            
            # Calculate if the notional date is before the modelling date
            datenewnot = (self.notionaldates[iAsset]-MD)
            if datenewnot.days >0: # 

            datefracoutnot = np.append(datefracout,datefrac)
            datesconsideredout = np.append(datesconsideredout,datesconsidered.astype(int))
        self.coupondatefrac = datefracout


        return [datesconsideredout, datefracout]



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

class CorporateBondPriced:
    def __init__(self, modellingdate,compounding):
        self.modellingdate = modellingdate
        self.compounding = compounding
        self.marketprice = []
        self.bookprice = 0
        self.sspread = []
        self.zspread = []
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

    def PriceBond(self, couponrates,notionalrates,couponmaturities, notionalmaturities,couponcf,notionalcf,sSpread,zSpread):
        nAsset = len(couponrates)
        self.marketprice = []

        for iAsset in range(0,nAsset):
            MV_CP = self.ratestodics(couponmaturities[iAsset],couponrates[iAsset]+sSpread[iAsset]+zSpread[iAsset], self.compounding) * couponcf[iAsset]
            MV_NOT = self.ratestodics(notionalmaturities[iAsset],notionalrates[iAsset]+sSpread[iAsset]+zSpread[iAsset],  self.compounding) * notionalcf[iAsset]
            MV = np.sum(MV_CP)+MV_NOT
            self.marketprice.append(np.array(MV))


    def OpenPriceBond(self, couponrates,notionalrates,couponmaturities, notionalmaturities,couponcf,notionalcf,sSpread,zSpread):

        MV_CP = self.ratestodics(couponmaturities,couponrates + sSpread + zSpread, self.compounding) * couponcf
        MV_NOT = self.ratestodics(notionalmaturities,notionalrates + sSpread + zSpread,  self.compounding) * notionalcf
        MV = np.sum(MV_CP) + MV_NOT

        return MV