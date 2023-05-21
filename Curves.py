import numpy as np
import pandas as pd

class Curves:
    def __init__(self, ufr, Precision, Tau, InitialDate, Country):
    
        self.InitialDate = InitialDate
        self.Country = Country
        self.StartDate = pd.DataFrame(data=None)
        self.FwdRates = pd.DataFrame(data=None)
        self.M_Obs = pd.DataFrame(data=None)
        self.r_Obs = pd.DataFrame(data=None)
        self.ufr = ufr
        self.Precision = Precision
        self.Tau = Tau
        self.alpha = pd.DataFrame(data=None)
        self.b = pd.DataFrame(data=None)

    def SWHeart(self, u, v, alpha):
    # SWHEART Calculate the heart of the Wilson function.
    # SWHeart(u, v, alpha) calculates the matrix H (Heart of the Wilson
    # function) for maturities specified by vectors u and v. The formula is
    # taken from the EIOPA technical specifications paragraph 132.
    #
    # Arguments:  
    #    u =     n_1 x 1 vector of maturities. Ex. u = [1; 3]
    #    v =     n_2 x 1 vector of maturities. Ex. v = [1; 2; 3; 5]
    #    alpha = 1 x 1 floating number representing the convergence speed parameter alpha. Ex. alpha = 0.05
    #
    # Returns:
    #    n_1 x n_2 matrix representing the Heart of the Wilson function for selected maturities and parameter alpha. H is calculated as in the paragraph 132 of the EIOPA documentation. 
    #
    # For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf

    
        u_Mat = np.tile(u, [v.size, 1]).transpose()
        v_Mat = np.tile(v, [u.size, 1])
        return 0.5 * (alpha * (u_Mat + v_Mat) + np.exp(-alpha * (u_Mat + v_Mat)) - alpha * np.absolute(u_Mat-v_Mat) - np.exp(-alpha * np.absolute(u_Mat-v_Mat))); # Heart of the Wilson function from paragraph 132

    def SWCalibrate(self, r, M, ufr, alpha):
    # SWCALIBRATE Calculate the calibration vector using a Smith-Wilson algorithm
    # b = SWCalibrate(r, T, ufr, alpha) calculates the vector b used for
    # interpolation and extrapolation of rates.
    #
    # Arguments: 
    #    r =     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable zero coupon bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
    #    M =     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u=[[1], [3]]
    #    ufr =   1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
    #    alpha = 1 x 1 floating number representing the convergence speed parameter alpha. Ex. alpha = 0.05
    #
    # Returns:
    #    n x 1 ndarray array for the calibration vector needed to interpolate and extrapolate b =[[14], [-21]]
    #    rates
    # For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf

        C = np.identity(M.size)
        p = (1+r) **(-M)  # Transform rates to implied market prices of a ZCB bond
        d = np.exp(-np.log(1+ufr) * M)    # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                  # Matrix Q described in paragraph 139
        q = C.transpose() @ d                         # Vector q described in paragraph 139
        H = self.SWHeart(M, M, alpha) # Heart of the Wilson function from paragraph 132

        return np.linalg.inv(Q.transpose() @ H @ Q) @ (p-q)          # Calibration vector b from paragraph 149
    
    def SWExtrapolate(self, M_Target, M_Obs, b, ufr, alpha):
    # SWEXTRAPOLATE Interpolate or/and extrapolate rates for targeted maturities using a Smith-Wilson algorithm.
    # r = SWExtrapolate(T_Target,T_Obs, b, ufr, alpha) calculates the rates for maturities specified in M_Target using the calibration vector b.
    #
    # Arguments: 
    #    M_Target = k x 1 ndarray. Each element represents a bond maturity of interest. Ex. M_Target = [[1], [2], [3], [5]]
    #    M_Obs =    n x 1 ndarray. Observed bond maturities used for calibrating the calibration vector b. Ex. M_Obs = [[1], [3]]
    #    b =        n x 1 ndarray calibration vector calculated on observed bonds.
    #    ufr =      1 x 1 floating number, representing the ultimate forward rate.
    #       Ex. ufr = 0.042
    #    alpha =    1 x 1 floating number representing the convergence speed parameter alpha. Ex. alpha = 0.05
    #    rates
    #
    # Returns:
    #    k x 1 ndarray. Represents the targeted rates for a zero-coupon bond. Each rate belongs to a targeted zero-coupon bond with a maturity from T_Target. Ex. r = [0.0024; 0.0029; 0.0034; 0.0039]
    #
    # For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf

        C = np.identity(M_Obs.size)
        d = np.exp(-np.log(1+ufr) * M_Obs)                                                # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                                                             # Matrix Q described in paragraph 139
        H = self.SWHeart(M_Target, M_Obs, alpha)                                          # Heart of the Wilson function from paragraph 132
        p = np.exp(-np.log(1+ufr)* M_Target) + np.diag(np.exp(-np.log(1+ufr) * M_Target)) @ H @ Q @ b # Discount pricing function for targeted maturities from paragraph 147
        return p ** (-1/ M_Target) -1 # Convert obtained prices to rates and return prices

    def Galfa(self, M_Obs: np.ndarray, r_Obs: np.ndarray, ufr, alpha, Tau):
        """
        Calculates the gap at the convergence point between the allowable tolerance Tau and the curve extrapolated using the Smith-Wilson algorithm.
        interpolation and extrapolation of rates.
        
        Args:
            M_Obs = n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u=[[1], [3]]
            r_Obs = n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            ufr =   1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            alpha = 1 x 1 floating number representing the convergence speed parameter alpha. Ex. alpha = 0.05
            Tau =   1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. Tau = 0.00001
        
        Returns:
            1 x 1 floating number representing the distance between ufr input and the maximum allowed discrepancy Tau 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> from SWExtrapolate import SWExtrapolate as SWExtrapolate
            >>> M_Obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_Obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> alfa = 0.15
            >>> ufr = 0.04
            >>> Precision = 0.0000000001
            >>> Tau = 0.0001
            >>> Galfa(M_Obs, r_Obs, ufr, alfa, Tau)
            [Out] -8.544212205612438e-05

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """
        
        U = max(M_Obs)                                # Find maximum liquid maturity from input
        T = max(U + 40, 60)                             # Define the convergence point as defined in paragraph 120 and again in 157
        C = np.identity(M_Obs.size)                   # Construct cash flow matrix described in paragraph 137 assuming the input is ZCB bonds with notional value of 1
        d = np.exp(-np.log(1 + ufr) * M_Obs)            # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                            # Matrix Q described in paragraph 139
        b = self.SWCalibrate(r_Obs, M_Obs, ufr, alpha)     # Calculate the calibration vector b using the equation from paragraph 149

        K = (1+alpha * M_Obs @ Q@ b) / (np.sinh(alpha * M_Obs.transpose())@ Q@ b) # Calculate kappa as defined in the paragraph 155
        return( alpha/np.abs(1 - K*np.exp(alpha*T))-Tau) # Size of the gap at the convergence point between the allowable tolerance Tau and the actual curve. Defined in paragraph 158

    def BisectionAlpha(self, xStart, xEnd, M_Obs, r_Obs, ufr, Tau, Precision, maxIter):
        """
        Bisection root finding algorithm for finding the root of a function. The function here is the allowed difference between the ultimate forward rate and the extrapolated curve using Smith & Wilson.

        Args:
            xStart =    1 x 1 floating number representing the minimum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.05
            xEnd =      1 x 1 floating number representing the maximum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.8
            M_Obs =     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u = [[1], [3]]
            r_Obs =     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            ufr  =      1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            Tau =       1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. Tau = 0.00001
            Precision = 1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            maxIter =   1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
        
        Returns:
            1 x 1 floating number representing the optimal value of the parameter alpha 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> M_Obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_Obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> xStart = 0.05
            >>> xEnd = 0.5
            >>> maxIter = 1000
            >>> alfa = 0.15
            >>> ufr = 0.042
            >>> Precision = 0.0000000001
            >>> Tau = 0.0001
            >>> BisectionAlpha(xStart, xEnd, M_Obs, r_Obs, ufr, Tau, Precision, maxIter)
            [Out] 0.11549789285636511

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf and https://en.wikipedia.org/wiki/Bisection_method
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """   

        yStart = self.Galfa(M_Obs, r_Obs, ufr, xStart, Tau) # Check if the initial point is a solution
        yEnd = self.Galfa(M_Obs, r_Obs, ufr, xEnd, Tau) # Check if the final point is a solution
        if np.abs(yStart) < Precision:
            #self.alpha = xStart # If initial point already satisfies the conditions return start point
            return xStart
        if np.abs(yEnd) < Precision:
            #self.alpha = xEnd
            return xEnd # If final point already satisfies the conditions return end point
        iIter = 0
        while iIter <= maxIter:
            xMid = (xEnd+xStart)/2 # calculate mid-point 
            yMid = self.Galfa(M_Obs, r_Obs, ufr, xMid, Tau) # What is the solution at midpoint

            if (yMid == 0 or (xEnd-xStart)/2 < Precision): # Solution found
                #self.alpha = xMid
                return xMid
            else: # Solution not found
                iIter += 1
                if np.sign(yMid) == np.sign(yStart): # If the start point and the middle point have the same sign, then the root must be in the second half of the interval   
                    xStart = xMid
                else: # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    xEnd = xMid
        #self.alpha = None
        return None