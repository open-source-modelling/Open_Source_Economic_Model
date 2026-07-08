from dataclasses import dataclass

import pandas as pd


@dataclass
class Society:
    """
    Demographic tables used by liability decrement sampling.

    Parameters
    ----------
    :type mortality_male: pd.Series
        Annual mortality rates indexed by integer age.
    :type mortality_female: pd.Series
        Annual mortality rates indexed by integer age.
    """

    mortality_male: pd.Series
    mortality_female: pd.Series

    def mortality_rate(self, age: int, is_female: bool) -> float:
        """
        Look up the annual mortality rate q at age, clamping to table bounds.

        Parameters
        ----------
        :type age: int
            Age in completed years.
        :type is_female: bool
            If True, use the female table; otherwise the male table.

        Returns
        -------
        :rtype: float
            Annual mortality probability in [0, 1].
        """
        table = self.mortality_female if is_female else self.mortality_male
        min_age = int(table.index.min())
        max_age = int(table.index.max())
        clamped = min(max(age, min_age), max_age)
        return float(table.loc[clamped])
