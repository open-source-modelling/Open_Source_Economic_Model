"""Shared per-module file-logger setup.

`main.py`, `EquityClasses.py`, and `BondClasses.py` each want their own
logger writing to their own `.log` file (`ALM.log`, `EquityClasses.log`,
`BondClass.log`). Previously each module duplicated the same
getLogger/setLevel/Formatter/FileHandler boilerplate independently, with one
copy carrying a formatter typo (`%(mesage)s`). This module centralizes that
setup so there is one formatter to get right and one place to change it.
"""
import logging

DEFAULT_FORMAT = "%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])"


def get_file_logger(name: str, log_filename: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a logger named `name` with a FileHandler writing to `log_filename`.

    Parameters
    ----------
    :type name: str
        Logger name, conventionally the importing module's `__name__`.
    :type log_filename: str
        Log file path (relative paths resolve against the current working
        directory, matching the existing per-module log files).
    :type level: int
        Logging level for this logger (e.g. `logging.DEBUG`).

    Returns
    -------
    :rtype: logging.Logger
        The configured logger. Safe to call on every import: if a
        FileHandler for `log_filename` is already attached, it is not
        duplicated.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    has_handler = any(
        isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith(log_filename)
        for handler in logger.handlers
    )
    if not has_handler:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        logger.addHandler(file_handler)

    return logger
