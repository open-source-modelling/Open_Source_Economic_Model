"""Tests for get_file_logger and set_log_level: every log file goes into the Logs folder, and one level applies to all of them."""
import logging

import pytest

import osem.BondClasses
import osem.EquityClasses
import osem.ReportClass
from osem.logging_utils import LOG_FOLDER, PACKAGE_LOGGER, get_file_logger, set_log_level


@pytest.fixture
def fresh_logger_name():
    # Loggers are global, so each test uses its own name and closes its handlers afterwards
    # (an open file would stop pytest from removing tmp_path on Windows). The package level is
    # put back too, as other tests and the module loggers share it.
    name = "osem.test_logging_utils"
    yield name
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    set_log_level(logging.DEBUG)


def test_log_file_is_written_to_the_logs_folder(tmp_path, monkeypatch, fresh_logger_name):
    monkeypatch.chdir(tmp_path)

    logger = get_file_logger(fresh_logger_name, "Test.log")
    logger.info("hello")
    for handler in logger.handlers:
        handler.flush()

    assert LOG_FOLDER == "Logs"
    assert "hello" in (tmp_path / "Logs" / "Test.log").read_text()
    assert not (tmp_path / "Test.log").exists()


def test_existing_logs_folder_is_reused(tmp_path, monkeypatch, fresh_logger_name):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Logs" / "Other.log").write_text("kept")

    get_file_logger(fresh_logger_name, "Test.log")

    assert (tmp_path / "Logs" / "Other.log").read_text() == "kept"


def test_handler_is_not_duplicated(tmp_path, monkeypatch, fresh_logger_name):
    monkeypatch.chdir(tmp_path)

    get_file_logger(fresh_logger_name, "Test.log")
    logger = get_file_logger(fresh_logger_name, "Test.log")

    assert len([handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]) == 1


def test_logger_outside_the_osem_package_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # "__main__" is what main.py's __name__ is when run with python -m osem.main
    with pytest.raises(ValueError, match="must start with 'osem.'"):
        get_file_logger("__main__", "Test.log")


def test_set_log_level_applies_to_every_module_logger(fresh_logger_name):
    module_loggers = [osem.BondClasses.logger, osem.EquityClasses.logger, osem.ReportClass.logger]

    set_log_level(logging.WARNING)

    assert logging.getLogger(PACKAGE_LOGGER).level == logging.WARNING
    for logger in module_loggers:
        assert logger.level == logging.NOTSET  # No level of its own to override the package one
        assert not logger.isEnabledFor(logging.INFO)
        assert logger.isEnabledFor(logging.WARNING)

    set_log_level(logging.DEBUG)

    assert all(logger.isEnabledFor(logging.DEBUG) for logger in module_loggers)


def test_messages_below_the_level_are_not_written(tmp_path, monkeypatch, fresh_logger_name):
    monkeypatch.chdir(tmp_path)
    logger = get_file_logger(fresh_logger_name, "Test.log")

    set_log_level(logging.WARNING)
    logger.info("hidden")
    logger.warning("shown")
    for handler in logger.handlers:
        handler.flush()

    text = (tmp_path / "Logs" / "Test.log").read_text()
    assert "shown" in text
    assert "hidden" not in text
