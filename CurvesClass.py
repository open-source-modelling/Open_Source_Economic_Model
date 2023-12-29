import numpy as np
import pandas as pd

class Curves:
    def __init__(self, ufr: float, precision: float, tau: float, initial_date, country: str):
    
        self.initial_date = initial_date
        self.country = country
        self.start_date = pd.DataFrame(data=None)
        self.fwd_rates = pd.DataFrame(data=None)
        self.m_obs_ini = pd.DataFrame(data=None,index=None, columns=["Maturity"])
        self.r_obs_ini = pd.DataFrame(data= None, index=None, columns=["Yield"])
        self.m_obs = pd.DataFrame(data=None,index=None, columns=["Maturities_year_0"])
        self.r_obs = pd.DataFrame(data= None, index=None, columns=["Yield_year_0"])
        self.ufr = ufr
        self.precision = precision
        self.tau = tau
        self.alpha_ini = pd.DataFrame(data=None, columns=["Alpha_year"], dtype="float64")
        self.alpha = pd.DataFrame(data=None, columns=["Alpha_year_0"], dtype="float64")
        self.b = pd.DataFrame(data=None, columns=["Calibration_year_0"])

    def SetObservedTermStructure(self, maturity_vec, yield_vec):
        self.m_obs_ini = pd.DataFrame(data= maturity_vec, index=None, columns=["Maturity"])
        self.r_obs_ini = pd.DataFrame(data= yield_vec, index=None, columns=["Yield"])


    def CalcFwdRates(self):
        fwdata0 = 1 + self.r_obs_ini["Yield"][0] # First forward rate is equal to the first spot rate
        fwdata = ((1 + self.r_obs_ini["Yield"]) ** self.m_obs_ini["Maturity"])/((1 + self.r_obs_ini["Yield"].shift(periods=1)) ** self.m_obs_ini["Maturity"].shift(periods=1))
        out = np.insert(fwdata.values[1:], 0, fwdata0) # First forward in fwdata is NaN. instead fwdata0 is inserted at the start
        self.fwd_rates = pd.DataFrame(data=out, index=None, columns=["Forward"])


    def ProjectForwardRate(self,N):
        """
        Calculate the projected spot curve from pre calculated 1-year forward curve. Each column represents
        the spot curve starting 1 year later than the previous column. Calling this function populates/overwrites
        the r_obs property of the instance.

        Parameters
        ----------
        self: Curves class instance
            The Curves class instance with populated fwd_rates
        :type N: integer
            The number of required yearly projections
        """
        if N<0:
            return "N should be greater than 0"

        # Calculate first spot rate and initiate the dataframe
        spot = ((1+self.fwd_rates["Forward"]).cumprod(axis=None)**(1/self.m_obs_ini["Maturity"])-1)-1
        self.m_obs["Maturities_year_0"] = self.m_obs_ini["Maturity"].values
        self.r_obs["Yield year_0"] = spot.values

        if N>=1:
            for year in range(1,N):
                maturities = self.m_obs_ini["Maturity"]-year
                spot = ((1+self.fwd_rates["Forward"][year:]).cumprod(axis=None)**(1/maturities)-1)[year:]-1
                self.m_obs = self.m_obs.join(pd.Series(data=maturities.values[year:], index=None, name="Maturities_year_"+str(year)))
                self.r_obs = self.r_obs.join(pd.Series(data=spot.values, index=None, name="Yield_year_"+str(year)))


    def SWHeart(self, u: np.ndarray, v: np.ndarray, alpha: float):
        """
        SWHEART Calculate the heart of the Wilson function.
        SWHeart(u, v, alpha) calculates the matrix H (Heart of the Wilson
        function) for maturities specified by vectors u and v. The formula is
        taken from the EIOPA technical specifications paragraph 132.
    
        Parameters
        ----------
            :type u : n_1 x 1 numpy array of maturities. Ex. u = [1; 3]
            :type v : n_2 x 1 numpy array of maturities. Ex. v = [1; 2; 3; 5]
            :type alpha : float the convergence speed parameter alpha. Ex. alpha = 0.05
    
        Returns
        -------
            :rtype n_1 x n_2 numpy array matrix representing the Heart of the Wilson function for 
            selected maturities and parameter alpha. 
            H is calculated as in the paragraph 132 of the EIOPA documentation. 
    
        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf
        """
    
        u_mat = np.tile(u, [v.size, 1]).transpose()
        v_mat = np.tile(v, [u.size, 1])
        return 0.5 * (alpha * (u_mat + v_mat) + np.exp(-alpha * (u_mat + v_mat)) - alpha * np.absolute(u_mat-v_mat) - np.exp(-alpha * np.absolute(u_mat-v_mat))); # Heart of the Wilson function from paragraph 132

    def SWCalibrate(self, r: np.ndarray, M: np.ndarray, ufr: float, alpha: float):
        """
        SWCALIBRATE Calculate the calibration vector using a Smith-Wilson algorithm
        b = SWCalibrate(r, T, ufr, alpha) calculates the vector b used for
        interpolation and extrapolation of rates.
        
        Parameters
        ----------
        :type r :     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable zero coupon bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
        :type M :     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u=[[1], [3]]
        :type ufr :   float representing the ultimate forward rate. Ex. ufr = 0.042
        :type alpha : float representing the convergence speed parameter alpha. Ex. alpha = 0.05
        
        Returns
        -------
        :rtype n x 1 ndarray array for the calibration vector needed to interpolate and extrapolate b =[[14], [-21]]
        rates

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf
        """
        C = np.identity(M.size)
        p = (1+r) **(-M)  # Transform rates to implied market prices of a ZCB bond
        d = np.exp(-np.log(1+ufr) * M)    # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                  # Matrix Q described in paragraph 139
        q = C.transpose() @ d                         # Vector q described in paragraph 139
        H = self.SWHeart(M, M, alpha) # Heart of the Wilson function from paragraph 132

        return np.linalg.inv(Q.transpose() @ H @ Q) @ (p-q)          # Calibration vector b from paragraph 149
    
    def SWExtrapolate(self, m_target: np.ndarray, m_obs: np.ndarray, b: np.ndarray, ufr: float, alpha: float):
        """"
        SWEXTRAPOLATE Interpolate or/and extrapolate rates for targeted maturities using a Smith-Wilson algorithm.
        r = SWExtrapolate(m_target,m_obs, b, ufr, alpha) calculates the rates for maturities specified in M_Target using the calibration vector b.
        
        Parameters
        ----------
            :type m_target : k x 1 ndarray. Each element represents a bond maturity of interest. Ex. M_Target = [[1], [2], [3], [5]]
            :type m_obs :    n x 1 ndarray. Observed bond maturities used for calibrating the calibration vector b. Ex. M_Obs = [[1], [3]]
            :type b :        n x 1 ndarray calibration vector calculated on observed bonds.
            :type ufr :      float representing the ultimate forward rate.
            Ex. ufr = 0.042
            :type alpha :    float representing the convergence speed parameter alpha. Ex. alpha = 0.05
            rates.
        
        Returns
        -------
        :rtype k x 1 ndarray. Represents the targeted rates for a zero-coupon bond. Each rate belongs to a targeted zero-coupon bond with a maturity from T_Target. Ex. r = [0.0024; 0.0029; 0.0034; 0.0039]
        
        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf
        """
        C = np.identity(m_obs.size)
        d = np.exp(-np.log(1+ufr) * m_obs)                                                # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                                                             # Matrix Q described in paragraph 139
        H = self.SWHeart(m_target, m_obs, alpha)                                          # Heart of the Wilson function from paragraph 132
        p = np.exp(-np.log(1+ufr)* m_target) + np.diag(np.exp(-np.log(1+ufr) * m_target)) @ H @ Q @ b # Discount pricing function for targeted maturities from paragraph 147
        return p ** (-1/ m_target) -1 # Convert obtained prices to rates and return prices

    def Galfa(self, m_obs: np.ndarray, r_obs: np.ndarray, ufr: float, alpha: float, tau: float):
        """
        Calculates the gap at the convergence point between the allowable tolerance tau and the curve extrapolated using the Smith-Wilson algorithm.
        interpolation and extrapolation of rates.
        
        Parameters
        ----------
            :type m_obs : n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u=[[1], [3]]
            :type r_obs : n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            :type ufr :   1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            :type alpha : 1 x 1 floating number representing the convergence speed parameter alpha. Ex. alpha = 0.05
            :type tau :   1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. tau = 0.00001
        
        Returns
        -------
            :rtype float representing the distance between ufr input and the maximum allowed discrepancy tau 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> from SWExtrapolate import SWExtrapolate as SWExtrapolate
            >>> m_obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> alfa = 0.15
            >>> ufr = 0.04
            >>> precision = 0.0000000001
            >>> tau = 0.0001
            >>> Galfa(m_obs, r_obs, ufr, alfa, tau)
            [Out] -8.544212205612438e-05

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """
        
        U = max(m_obs)                                # Find maximum liquid maturity from input
        T = max(U + 40, 60)                             # Define the convergence point as defined in paragraph 120 and again in 157
        C = np.identity(m_obs.size)                   # Construct cash flow matrix described in paragraph 137 assuming the input is ZCB bonds with notional value of 1
        d = np.exp(-np.log(1 + ufr) * m_obs)            # Calculate vector d described in paragraph 138
        Q = np.diag(d) @ C                            # Matrix Q described in paragraph 139
        b = self.SWCalibrate(r_obs, m_obs, ufr, alpha)     # Calculate the calibration vector b using the equation from paragraph 149

        K = (1+alpha * m_obs @ Q@ b) / (np.sinh(alpha * m_obs.transpose())@ Q@ b) # Calculate kappa as defined in the paragraph 155
        return( alpha/np.abs(1 - K*np.exp(alpha*T))-tau) # Size of the gap at the convergence point between the allowable tolerance Tau and the actual curve. Defined in paragraph 158

    def BisectionAlpha(self, x_start, x_end, m_obs, r_obs, ufr, tau, precision, max_iter):
        """
        Bisection root finding algorithm for finding the root of a function. The function here is the allowed difference between the ultimate forward rate and the extrapolated curve using Smith & Wilson.

        Parameters
        ----------
            :type x_start :   1 x 1 floating number representing the minimum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.05
            :type x_end :     1 x 1 floating number representing the maximum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.8
            :type m_obs :     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u = [[1], [3]]
            :type r_obs :     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            :type ufr  :      1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            :type tau :       1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. Tau = 0.00001
            :type precision : 1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            :type max_iter :  1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
        
        Returns
        -------
            :rtype float representing the optimal value of the parameter alpha 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> m_obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> x_start = 0.05
            >>> x_end = 0.5
            >>> max_iter = 1000
            >>> alfa = 0.15
            >>> ufr = 0.042
            >>> precision = 0.0000000001
            >>> tau = 0.0001
            >>> BisectionAlpha(x_start, x_end, m_obs, r_obs, ufr, tau, precision, max_iter)
            [Out] 0.11549789285636511

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf and https://en.wikipedia.org/wiki/Bisection_method
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """   

        y_start = self.Galfa(m_obs, r_obs, ufr, x_start, tau) # Check if the initial point is a solution
        y_end = self.Galfa(m_obs, r_obs, ufr, x_end, tau) # Check if the final point is a solution
        if np.abs(y_start) < precision:
            #self.alpha = xStart # If initial point already satisfies the conditions return start point
            return x_start
        if np.abs(y_end) < precision:
            #self.alpha = xEnd
            return x_end # If final point already satisfies the conditions return end point
        i_iter = 0
        while i_iter <= max_iter:
            x_mid = (x_end+x_start)/2 # calculate mid-point 
            y_mid = self.Galfa(m_obs, r_obs, ufr, x_mid, tau) # What is the solution at midpoint

            if (y_mid == 0 or (x_end-x_start)/2 < precision): # Solution found
                #self.alpha = xMid
                return x_mid
            else: # Solution not found
                i_iter += 1
                if np.sign(y_mid) == np.sign(y_start): # If the start point and the middle point have the same sign, then the root must be in the second half of the interval   
                    x_start = x_mid
                else: # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = x_mid
        #self.alpha = None
        return None