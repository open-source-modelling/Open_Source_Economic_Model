import numpy as np
import datetime as dt

def CouponBond(notional, couponrate, issuedate, maturitydate,frequency):
    startdate = issuedate.year
    enddate = maturitydate.year
    month =  issuedate.month
    day = issuedate.day
    couponsize = notional*couponrate
    # Missing what if date is 31,30
    # Missing other frequencies
    coupondate = np.array([]) 
    if frequency == 1:
        for selectedyear in range(startdate,enddate+1):
            coupondate = np.append(coupondate,dt.date(selectedyear,month,day))
    elif frequency == 2:
        #todo
        print("Not completed")
    
    notionaldate = np.array([maturitydate])
    couponcf = np.ones_like(coupondate)*couponsize
    notionalcf = np.array([notional])

    return[notionalcf, couponcf, notionaldate, coupondate]
