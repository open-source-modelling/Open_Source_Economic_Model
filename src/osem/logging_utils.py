"""Shared per-module file-logger setup.

`main.py`, `ReportClass.py`, `EquityClasses.py`, and `BondClasses.py` each
want a logger writing to a `.log` file (`ALM.log`, `EquityClasses.log`,
`BondClass.log`). Previously each module duplicated the same
getLogger/setLevel/Formatter/FileHandler boilerplate independently, with one
copy carrying a formatter typo (`%(mesage)s`). This module centralizes that
setup so there is one formatter to get right and one place to change it, and
puts every log file in the `Logs` folder.

The module loggers have no level of their own. They take the level of the
`osem` package logger, so `set_log_level` sets the level of every log file at
once; `main.py` calls it with the `[LOGGING]` level of `ALM.ini`.
"""
import logging
import os

DEFAULT_FORMAT = "%(levelname)s:%(name)s:(%(asctime)s):%(message)s (Line: %(lineno)d [%(filename)s])"

# Relative to the working directory, like the Input and Output folders, so a run from the
# repository root logs to <repository>/Logs
LOG_FOLDER = "Logs"

# Parent of every module logger. Until main applies ALM.ini, and in notebooks and tests that do
# not run main, it lets everything through.
PACKAGE_LOGGER = "osem"
logging.getLogger(PACKAGE_LOGGER).setLevel(logging.DEBUG)


def get_file_logger(name: str, log_filename: str) -> logging.Logger:
    """
    Return a logger named `name` with a FileHandler writing to `log_filename` in the Logs
    folder. The folder is created if it does not exist. The logger takes its level from the
    osem package logger, which set_log_level sets.

    Parameters
    ----------
    name: str
        Logger name inside the osem package, conventionally the importing module's `__name__`.
        Ex. name = "osem.BondClasses"
    log_filename: str
        Name of the log file inside the Logs folder. Ex. log_filename = "ALM.log"

    Returns
    -------
    logging.Logger
        The configured logger. Safe to call on every import: if a
        FileHandler for the same file is already attached, it is not
        duplicated.

    Raises
    ------
    ValueError
        If name is not inside the osem package, as set_log_level would not reach the logger
    """
    if not name.startswith(PACKAGE_LOGGER + "."):
        raise ValueError(
            f"Logger name {name!r} must start with '{PACKAGE_LOGGER}.' so that it takes the level "
            f"set by set_log_level"
        )
    logger = logging.getLogger(name)

    os.makedirs(LOG_FOLDER, exist_ok=True)
    log_path = os.path.abspath(os.path.join(LOG_FOLDER, log_filename))
    has_handler = any(
        isinstance(handler, logging.FileHandler) and handler.baseFilename == log_path
        for handler in logger.handlers
    )
    if not has_handler:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        logger.addHandler(file_handler)

    return logger


def set_log_level(level: int) -> None:
    """
    Set the level of every OSEM module logger, through the osem package logger they take their
    level from. Messages below the level are dropped before they reach a log file or the console.

    Parameters
    ----------
    level: int
        Logging level. Ex. level = logging.WARNING

    Returns
    -------
    None
    """
    logging.getLogger(PACKAGE_LOGGER).setLevel(level)
