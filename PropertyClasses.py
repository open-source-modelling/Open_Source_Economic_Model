import numpy as np
import datetime as dt

class Property:
    def __init__(self,propertyname, buydate, finaldate, frequency, divyield, growthrate, defprob, terminalvalue):
        self.propertyname = propertyname
        self.buydate = buydate
        self.finaldate = finaldate
        self.frequency = frequency
        self.divyield = divyield
        self.growthrate = growthrate
        self.defprob = defprob
        self.terminalvalue = terminalvalue
        self.dividenddates = []
        self.terminaldates =[]
        self.dividendcfs = []
        self.terminalcfs = []
