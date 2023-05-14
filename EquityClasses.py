import numpy as np
import datetime as dt

class Equity:
    def __init__(self,issuer, buydate, finaldate, frequency, divyield, growthrate, defprob, terminalvalue):
        self.issuer = issuer
        self.issuedate = buydate
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