import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import date, timedelta
from osem.CurvesClass import Curves
from osem.FrequencyClass import Frequency
from osem.SettingsClasses import Settings
from osem.logging_utils import get_file_logger
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Iterable, Iterator, Tuple, Type, cast

logger = get_file_logger(__name__, "BondClass.log")

class FixedCouponBond:
    """
    Cash flows, pricing and z-spread calibration shared by all fixed-coupon bonds that repay their
    notional in one payment at maturity. A bond instrument inherits these methods and declares the
    attributes below as fields of its own frozen dataclass.

    This class is not a dataclass, so it adds no fields and does not change the field order of the
    instruments that inherit from it. The annotations below only tell the type checker which
    attributes the methods read.
    """
    asset_id: str  # The ISIN for a real bond; any unique text for an illustrative one
    issue_date: date
    maturity_date: date
    coupon_rate: float  # Rate paid on each coupon date (per payment, not annualised); see coupon_amount
    notional_amount: float
    zspread: float  # Starting value only; calibrate_bond_portfolio replaces it at t0
    frequency: Frequency
    units: float
    market_price: float

    def _validate_bond_terms(self) -> None:
        """
        Check that the input values shared by all fixed-coupon bonds are valid. Called from the
        __post_init__ of each bond instrument.

        Parameters
        ----------
        self: FixedCouponBond instance

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If asset_id is not a non-empty string, units or notional_amount is not greater than
            0, coupon_rate is outside [0, 1], market_price is negative, frequency is not
            supported, or maturity_date is not after issue_date
        """
        # Read as object so the type check below is not dismissed as redundant: callers written
        # when bond ids were integers may still pass one.
        asset_id: object = self.asset_id
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"Asset ID must be a non-empty string, such as the bond's ISIN, not {asset_id!r}")
        if self.coupon_rate < 0:
            raise ValueError("Coupon rate cannot be negative")
        if self.coupon_rate > 1:
            raise ValueError("Coupon rate cannot be greater than 1")
        if self.units <= 0:
            raise ValueError("Units must be greater than 0")
        if self.market_price < 0:
            raise ValueError("Market price cannot be negative")
        if self.frequency not in [Frequency.MONTHLY, Frequency.QUARTERLY,Frequency.TRIANNUAL, Frequency.BIANNUAL, Frequency.ANNUAL]:
            raise ValueError("Frequency must be either Monthly, Quarterly,Triannual, SemiAnnual or Annual")
        if self.notional_amount <= 0:
            raise ValueError("Notional amount must be greater than 0")
        if self.maturity_date <= self.issue_date:
            raise ValueError("Maturity date cannot be before issue date")

    def coupon_amount(self) -> float:
        """
        Calculate the size of the coupon of the bond.
        The coupon amount is equal to the percentage of the notional value.

        coupon_rate is the rate paid on each coupon date, whatever the frequency. It is not an
        annualised rate: a bond with coupon_rate 0.02 and quarterly frequency pays 2% of the
        notional four times a year (8% a year). To model a bond quoted with an annual coupon c
        paid f times a year, set coupon_rate = c / f.

        Parameters
        ----------
        self: FixedCouponBond instance

        Returns
        -------
        :rtype float
            The monetary amount of the coupon
        """
        coupon_size = self.coupon_rate * self.notional_amount
        return coupon_size

    def generate_coupon_dates(self, modelling_date: date, end_date: date) -> Iterator[date]:
        """
        Generator yielding the coupon payment dates, counted from the issue date, that fall on or
        after the modelling date and on or before the earlier of end_date and the maturity date.

        Parameters
        ----------
        self: FixedCouponBond instance
        modelling_date: datetime.date
            The earliest date considered.
        end_date: datetime.date
            The latest date considered. A bond still alive at the end of the modelling window is
            redeemed there at par by create_single_maturity, so its coupons stop there as well.

        Returns
        -------
        this_date: datetime.date
            The date at which the coupon payment occurs
        """

        last_date = min(end_date, self.maturity_date)

        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.issue_date - delta
        while this_date < last_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date: #Not interested in past payments
                continue
            if this_date <= last_date:
                yield this_date


    def create_single_cash_flows(self, modelling_date: date, end_date: date) -> Dict[date, float]:
        """
        Create a dictionary of the bond's coupon cash flows. The return dictionary has dates of
        the cash flows as keys and monetary amounts as values.

        Parameters
        ----------
        self: FixedCouponBond instance
            The bond position of interest.
        modelling_date: datetime.date
            The date from which the coupon dates are considered.
        end_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        coupons: Dict[date, float]
            The coupon amount per unit of the bond on each payment date.
        """

        coupon_size = 0
        coupons: Dict[date, float] = {}
        for coupon_date in self.generate_coupon_dates(modelling_date, end_date):
            if coupon_date in coupons:  # If two cash flows on same date
                pass
                # dividends[dividend_date] = dividend_amount + dividends[dividend_date]
            else:  # New cash flow date
                coupon_size = self.coupon_amount()
                coupons.update({coupon_date: coupon_size})
        return coupons


    def create_single_maturity(self, end_date: date) -> Dict[date, float]:
        """
        Create a dictionary with the repayment of the bond's notional. It is paid on the maturity
        date, or at the end of the modelling window if the bond matures later.

        Parameters
        ----------
        self: FixedCouponBond instance
            The bond position of interest.
        end_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        principals: Dict[date, float]
            A single entry with the repayment date as the key and the notional amount per unit of
            the bond as the value.
        """

        principals: Dict[date, float] = {}
        terminal_amount = self.notional_amount
        terminal_date = min(end_date, self.maturity_date)
        principals.update({terminal_date: terminal_amount})
        return principals

    def term_to_maturity(self, modelling_date: date)->int:
        """
        Calculates the number of days between the modelling date and the redemption date of the bond

        Parameters
        ----------
        modelling_date: datetime.date
            The modelling start date

        Returns
        -------
        delta_days:int
        The number of days between the modelling date and the redemption date of the bond
        """
        delta: timedelta = self.maturity_date - modelling_date
        return delta.days

    def price_bond(self, coupons: Dict[date, float], notional: Dict[date, float], valuation_date: date, proj_period: int, curves: Curves, spread: float) -> float:
        """
        Calculate the price of a bond with defined coupon and notional payments using the
        yield curve obtained from the curves object with a fixed extra spread passed in spread.

        Parameters
        ----------
        self: FixedCouponBond instance
            The bond position of interest.
        coupons: dict
            A dictionary with dates of coupon cashflows as keys and monetary amounts as values.
        notional: dict
            A dictionary with dates of repayments of the notional as keys and monetary amounts as values.
        valuation_date: datetime.date
            The date at which the bond is valued. Cash-flow times are measured from this date.
        proj_period: int
            Projection year of valuation_date (0 at the modelling date). Selects the projected
            curve, whose maturities are measured from that year, so it must match valuation_date.
        curves: Curves
            Instance of the Curves class with calibrated term structure.
        spread: float
            Extra spread over the risk free rate applied to the bond.


        Returns
        -------
        disc_value: float
            The price of the bond.
        """

        date_frac: List[float] = []
        cash_flow: List[float] = []

        for key, value in coupons.items():
            date_tmp = (key-valuation_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)

        for key, value in notional.items():
            date_tmp = (key-valuation_date).days/365.25
            date_frac.append(date_tmp)
            cash_flow.append(value)

        date_frac_df = pd.DataFrame(data=date_frac, columns=["Date Fraction"])  # No need for DataFrames. Kept for compatibility
        cash_flow_df = pd.DataFrame(data=cash_flow, columns=["Cash flow"])

        #discount = curves.retrieve_rates(proj_period, date_frac_df.iloc[:, 0].to_numpy(), "Discount", spread)
        discount = curves.retrieve_rates(proj_period, np.asarray(date_frac_df.iloc[:, 0], dtype=np.float64), "Discount", spread)

        # Plain arrays, as in EquityShare: retrieve_rates returns a DataFrame, and np.sum of a
        # DataFrame gives one total per column (a 1-element Series) in pandas 2, not a number.
        nodisc_value = np.asarray(cash_flow_df, dtype=np.float64) * np.asarray(discount, dtype=np.float64)
        disc_value: float = float(np.sum(nodisc_value))
        return disc_value

    def bisection_spread(self, x_start: float, x_end:float, modelling_date:date, end_date:date, proj_period:int, curves: Curves, precision: float, max_iter:int)->float:
        """
        Bisection root finding algorithm for finding the spread at which the bond's cash flows,
        discounted with the risk free curve plus that spread, equal its market price.

        Parameters
        ----------
        self: FixedCouponBond instance
            The bond position of interest.
        x_start: float
            The lower bound of the spread. Ex. x_start = -0.2
        x_end: float
            The upper bound of the spread. Ex. x_end = 0.2
        modelling_date: date
            The date at which the bond is valued.
        end_date: date
            The date at which the modelling window closes.
        proj_period: int
            Projection year of modelling_date, which selects the projected curve.
        curves: Curves
            Instance of the Curves class with calibrated term structure.
        precision: float
            Stopping tolerance. A smaller value gives a more accurate result.
        max_iter: int
            Maximum number of iterations, to prevent an infinite loop.

        Returns
        -------
        float
            The spread implied by the market price and the yield curve.

        Raises
        ------
        ValueError
            If no solution lies between x_start and x_end
        TypeError
            If the calibration has not converged after max_iter iterations
        """

        dividends = self.create_single_cash_flows(modelling_date, end_date)
        terminal = self.create_single_maturity(end_date)
        y_start = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_start) - self.market_price

        dividends = self.create_single_cash_flows(modelling_date, end_date)
        terminal = self.create_single_maturity(end_date)
        y_end = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_end) - self.market_price

        if np.abs(y_start) < precision:
            return x_start
        if np.abs(y_end) < precision:
            return x_end  # If final point already satisfies the conditions return end point

        # The price falls monotonically in the spread, so a root exists only if the market price
        # lies between the two bracket prices. Without this check the loop below never sees a sign
        # change, walks x_start all the way up to x_end and returns the bracket bound as if it were
        # a calibrated spread. The max_iter guard does not catch that: the interval collapses to
        # `precision` in a few dozen halvings, long before max_iter is reached.
        if np.sign(y_start) == np.sign(y_end):
            raise ValueError(
                f"Spread calibration for bond {self.asset_id} has no solution in "
                f"[{x_start}, {x_end}]: the bond prices at {y_start + self.market_price:.4f} "
                f"and {y_end + self.market_price:.4f} at those spreads, but its market price is "
                f"{self.market_price}. Either widen the bracket, or check that coupon_rate is the "
                f"rate paid on each coupon date rather than an annualised one (see coupon_amount)."
            )

        i_iter = 0
        while i_iter <= max_iter:
            x_mid = (x_end + x_start) / 2  # calculate mid-point

            dividends = self.create_single_cash_flows(modelling_date, end_date)
            terminal = self.create_single_maturity(end_date)
            y_mid = self.price_bond(dividends, terminal, modelling_date, proj_period, curves, x_mid) - self.market_price
            if (y_mid == 0 or (x_end - x_start) / 2 < precision):  # Solution found
                return x_mid
            else:  # Solution not found
                i_iter += 1
                if np.sign(y_mid) == np.sign(
                        y_start):  # If the start point and the middle point have the same sign, then the root must be in the second half of the interval
                    x_start = x_mid
                else:  # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = x_mid

        raise TypeError("Spread calibration did not converge")


@dataclass(frozen=True)
class CorpBond(FixedCouponBond):
    """
    A corporate bond position. The country, sector and stress spreads, recovery rate and default
    probability are read from the input file but not used in pricing yet: like a GovBond, it is
    priced on the risk free curve plus the z-spread calibrated to its market price.
    """
    asset_id: str
    nace: str
    issuer: Optional[str]
    issue_date: date
    maturity_date: date
    coupon_rate: float  # Rate paid on each coupon date (per payment, not annualised); see coupon_amount
    notional_amount: float
    spread_country: float
    spread_sector: float
    zspread: float
    spread_stress: float
    frequency: Frequency
    recovery_rate: float
    default_probability: float
    units: float
    market_price: float

    def __post_init__(self):
        """
        Check that the bond's input values are valid.

        Parameters
        ----------
        self: CorpBond instance

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If any of the checks in FixedCouponBond._validate_bond_terms fails, or recovery_rate
            or default_probability is outside [0, 1]
        """
        self._validate_bond_terms()
        if self.recovery_rate < 0:
            raise ValueError("Recovery rate cannot be negative")
        if self.recovery_rate > 1:
            raise ValueError("Recovery rate cannot be greater than 1")
        if self.default_probability < 0:
            raise ValueError("Default probability cannot be negative")
        if self.default_probability > 1:
            raise ValueError("Default probability cannot be greater than 1")


@dataclass(frozen=True)
class GovBond(FixedCouponBond):
    """
    A government bond position. Its cash flows, pricing and z-spread calibration are the same as
    for a CorpBond. The sovereign's credit and liquidity risk enter only through the z-spread
    calibrated to its market price, so it has no sector spread, recovery rate or default
    probability. A CorpBond is priced the same way: it holds those fields, but its pricing does not
    use them yet. The bond is assumed to be in the currency of the run's risk free curve.
    """
    asset_id: str
    issuer_country: str
    issue_date: date
    maturity_date: date
    coupon_rate: float  # Rate paid on each coupon date (per payment, not annualised); see coupon_amount
    notional_amount: float
    zspread: float
    frequency: Frequency
    units: float
    market_price: float

    def __post_init__(self):
        """
        Check that the bond's input values are valid.

        Parameters
        ----------
        self: GovBond instance

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If any of the checks in FixedCouponBond._validate_bond_terms fails, or issuer_country
            is empty
        """
        self._validate_bond_terms()
        if not self.issuer_country.strip():
            raise ValueError("Issuer country cannot be empty")


def bonds_by_asset_id(bonds: Iterable[FixedCouponBond]) -> Dict[str, FixedCouponBond]:
    """
    Key bond positions by asset_id, ready for BondPortfolio. Corporate and government bonds share
    the bond DataFrames, which are indexed by asset_id, so an id can be used only once, within an
    input file and across the corporate and government files. A plain dict comprehension would
    keep the last bond with a repeated id and silently drop the others.

    Parameters
    ----------
    bonds: Iterable[FixedCouponBond]
        The bond positions. Ex. the output of get_corporate_bonds followed by get_government_bonds

    Returns
    -------
    Dict[str, FixedCouponBond]
        The bonds keyed by asset_id, in the order given

    Raises
    ------
    ValueError
        If two bonds have the same asset_id
    """
    by_id: Dict[str, FixedCouponBond] = {}
    for bond in bonds:
        if bond.asset_id in by_id:
            raise ValueError(
                f"Asset ID {bond.asset_id} is used by two bonds ({type(by_id[bond.asset_id]).__name__} "
                f"and {type(bond).__name__}). Bond asset IDs must be unique across the corporate and "
                f"government bond input files."
            )
        by_id[bond.asset_id] = bond
    return by_id


class BondPortfolio():
    def __init__(self, bonds: Optional[Dict[str, FixedCouponBond]] = None):
        """
        Initialize the BondPortfolio instance with the given bonds

        Parameters
        ----------
        bonds: Optional[Dict[str, FixedCouponBond]]
            The bond instances, keyed by asset_id. If None, the portfolio starts empty.

        Returns
        -------
        None
        """

        self.bonds: Dict[str, FixedCouponBond] = bonds if bonds is not None else {}

    def is_empty(self)-> bool:
        """
        Check whether the portfolio holds any bonds.

        Parameters
        ----------
        self: BondPortfolio instance

        Returns
        -------
        bool
            True if the portfolio has no bonds
        """
        return len(self.bonds) == 0

    def add(self, bond: FixedCouponBond) -> None:
        """
        Add a bond position to the portfolio.

        Parameters
        ----------
        bond : FixedCouponBond
            The bond position to add, keyed by asset_id in the portfolio dict.
        """
        self.bonds.update({bond.asset_id: bond})

    def asset_ids_of(self, bond_type: Type[FixedCouponBond]) -> List[str]:
        """
        List the asset ids of the bonds of one type. All bond types share the bond DataFrames, so
        these ids select the rows of that type in them.

        Parameters
        ----------
        self: BondPortfolio instance
        bond_type: Type[FixedCouponBond]
            The bond class to select. Ex. bond_type = GovBond

        Returns
        -------
        List[str]
            The asset ids of the bonds of that type, in portfolio order
        """
        return [asset_id for asset_id, bond in self.bonds.items() if isinstance(bond, bond_type)]

    def create_aggregate_coupon_dates(self, modelling_date:date, end_date:date) -> Dict[date, float]:
        """
        Add up the coupons of all bonds in the portfolio on each payment date, for dates
        on or after the modelling date. The amounts are per unit: units held are not applied.

        Parameters
        ----------
        self: BondPortfolio instance
            The BondPortfolio instance with populated initial portfolio.
        modelling_date: datetime.date
            The current assumed date inside the model
        end_date: datetime.date
            The end of the modelling window. No cash flows after this date are considered.

        Returns
        -------
        Dict[date, float]
            The payment dates as keys and the summed per-unit coupon amounts as values.
        """

        coupons: Dict[date, float] = {}
        bond: FixedCouponBond
        coupon_date: date
        for asset_id in self.bonds:
            bond = self.bonds[asset_id]
            for coupon_date in bond.generate_coupon_dates(modelling_date, end_date):
                if coupon_date in coupons:
                    coupons[coupon_date] += bond.coupon_amount()
                else:
                    coupons.update({coupon_date:bond.coupon_amount()})
        return coupons

    def create_coupon_flows(self, modelling_date: date, end_date: date) -> Dict[str, Dict[date, float]]:
        """
        Create a dictionary with the dates at which the coupons are paid out and the amounts per
        unit for each bond in the portfolio, for dates on or after the modelling date
        but not after the end date.

        Parameters
        ----------
        self: BondPortfolio instance
            The BondPortfolio instance with populated initial portfolio.
        modelling_date: datetime.date
            The date from which the coupon dates are considered.
        end_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        all_coupons: Dict[str, Dict[date, float]]
            A dictionary keyed by asset_id. Each value is a dictionary with the coupon dates as
            keys and the coupon amounts per unit as values.
        """
        all_coupons: Dict[str, Dict[date, float]] = {}
        bond: FixedCouponBond
        for asset_id in self.bonds:
            bond = self.bonds[asset_id]  # Select one asset position
            coupons = bond.create_single_cash_flows(modelling_date, end_date)
            all_coupons[asset_id] = coupons
        return all_coupons

    def create_maturity_flows(self, terminal_date: date) -> Dict[str, Dict[date, float]]:
        """
        Create a dictionary with the date at which each bond repays its notional and the amount
        per unit. If the maturity is after the end of the modelling window, the bond repays the
        notional at the end of the modelling window.

        Parameters
        ----------
        self: BondPortfolio instance
            The BondPortfolio instance with populated portfolio.
        terminal_date: datetime.date
            The last date that the model considers (end of the modelling window).

        Returns
        -------
        all_maturity: Dict[str, Dict[date, float]]
            A dictionary keyed by asset_id. Each value is a dictionary with the repayment date as
            the key and the notional amount per unit as the value.
        """

        all_maturity: Dict[str, Dict[date, float]] = {}
        principals: Dict[date, float] = {}
        bond: FixedCouponBond

        for asset_id in self.bonds:
            bond = self.bonds[asset_id]
            principals = bond.create_single_maturity(terminal_date)
            all_maturity[asset_id]=principals
        return all_maturity


    def unique_dates_profile(self, cash_flow_profile: Dict[str, Dict[date, float]]) -> List[date]:
        """
        Create a sorted list of dates at which there is a cash-flow event in any of the assets
        inside the portfolio.

        Parameters
        ----------
        self: BondPortfolio instance
            The BondPortfolio instance with populated portfolio.
        cash_flow_profile: Dict[str, Dict[date, float]]
            A dictionary keyed by asset_id, containing the date and size of each cash flow of
            that asset

        Returns
        -------
        List[date]
            A list of sorted unique dates containing at least one cash flow
        """

        unique_dates: List[date] = []
        for one_dividend_array in cash_flow_profile.values():
            for one_dividend_date in one_dividend_array.keys():  # for each dividend date of the selected asset
                if one_dividend_date in unique_dates:
                    continue
                unique_dates.append(one_dividend_date)

        return sorted(unique_dates)

    def init_bond_portfolio_to_dataframe(self, modelling_date: date) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Create the initial market price, z-spread and units DataFrames of the portfolio.

        Parameters
        ----------
        self: BondPortfolio instance
        modelling_date: datetime.date
            The date used as the name of the single column in each DataFrame

        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
            The market price, z-spread and units DataFrames, each with asset_id as the index and
            values stored as floats.
        """

        asset_keys = self.bonds.keys()

        market_price_tmp: List[float] = []
        zspread_tmp: List[float] = []
        asset_id_tmp: List[str] = []
        units_tmp: List[float] = []

        for key in asset_keys:
            market_price_tmp.append(self.bonds[key].market_price)
            zspread_tmp.append(self.bonds[key].zspread)
            asset_id_tmp.append(self.bonds[key].asset_id)
            units_tmp.append(self.bonds[key].units)

        # dtype=float explicitly: these frames are written back to with computed prices, spreads
        # and unit counts. A portfolio whose inputs happened to be whole numbers would otherwise
        # produce int64 columns, and pandas 3 refuses to store a float into one rather than
        # upcasting as earlier versions did.
        market_price = pd.DataFrame(data=market_price_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)

        zspread = pd.DataFrame(data=zspread_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)

        units = pd.DataFrame(data=units_tmp, index=asset_id_tmp, columns=[modelling_date], dtype=float)

        return market_price, zspread, units


    def create_maturity_cashflow(self, modelling_date: date) -> Dict[date, float]:
        """
        Add up the notional amounts of all bonds in the portfolio on each maturity date.
        The amounts are per unit: units held are not applied. Unlike create_maturity_flows, dates
        are not limited to the modelling window.

        Parameters
        ----------
        self: BondPortfolio instance
        modelling_date: date
            Not used in the calculation.

        Returns
        -------
        Dict[date, float]
            The maturity dates as keys and the summed notional amounts as values.
        """
        maturities: Dict[date, float] = {}
        bond: FixedCouponBond

        for asset_id in self.bonds:
            bond = self.bonds[asset_id]
            if bond.maturity_date in maturities:
                maturities[bond.maturity_date] += bond.notional_amount
            else:
                maturities.update({bond.maturity_date:bond.notional_amount})
        return maturities

    def price_bond_portfolio(self, coupon_df: pd.DataFrame, notional_df: pd.DataFrame, proj_period: int, curves: Curves, bond_zspread_df: pd.DataFrame, bond_price_df: pd.DataFrame, date_of_interest: date) -> pd.DataFrame:
        """
        Price each bond in coupon_df on date_of_interest and store the prices in bond_price_df.

        Parameters
        ----------
        coupon_df: pd.DataFrame
            Remaining coupon amounts per unit (rows = asset_id, columns = dates).
        notional_df: pd.DataFrame
            Remaining notional repayments per unit (rows = asset_id, columns = dates).
        proj_period: int
            Projection year of date_of_interest (0 at the modelling date); selects the projected curve.
        curves: Curves
            Instance of the Curves class with calibrated term structure.
        bond_zspread_df: pd.DataFrame
            Z-spread of each bond, read from the first column.
        bond_price_df: pd.DataFrame
            Price of each bond. Updated in place for date_of_interest.
        date_of_interest: date
            Valuation date. Remaining cash flows are discounted to this date.

        Returns
        -------
        pd.DataFrame
            bond_price_df with the prices for date_of_interest.
        """
        asset_id: str
        for asset_id in coupon_df.index:
            coupons = cast(Dict[date, float], coupon_df.loc[asset_id].to_dict())
            notional = cast(Dict[date, float], notional_df.loc[asset_id].to_dict())
            zspread = cast(float, bond_zspread_df.loc[asset_id].iloc[0])
            price: float = self.bonds[asset_id].price_bond(coupons, notional, date_of_interest, proj_period, curves, zspread)
            bond_price_df.loc[asset_id, date_of_interest] = price

        return bond_price_df

    def calibrate_bond_portfolio(self, zspread_df: pd.DataFrame, settings: Settings, proj_period: int, curves: Curves) -> pd.DataFrame:
        """
        Calibrate z-spreads for all bonds in the portfolio using bisection.

        Parameters
        ----------
        self: BondPortfolio instance
        zspread_df: pd.DataFrame
            Initial z-spreads for each bond
        settings: Settings
            Object with modelling dates and end date
        proj_period: int
            Projection period index for curve retrieval
        curves: Curves
            Object with calibrated term structure

        Returns
        -------
        pd.DataFrame
            Updated z-spread DataFrame with calibrated spreads
        """
        for asset_id in zspread_df.index:
            calibrated_spread: float = self.bonds[asset_id].bisection_spread(
                x_start=-0.2,
                x_end=0.2,
                modelling_date=settings.modelling_date,
                end_date=settings.end_date,
                proj_period=proj_period,
                curves=curves,
                precision=1e-8,
                max_iter=100000,
            )
            zspread_df.loc[asset_id, settings.modelling_date] = calibrated_spread
        return zspread_df
