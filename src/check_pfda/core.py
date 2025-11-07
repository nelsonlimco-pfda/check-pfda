"""Collect tests and run them on supplied code."""

import os
from pathlib import Path
import sys
import logging


from click import echo, secho
import pytest
from check_pfda.utils import (get_current_assignment, _add_to_path, _recurse_to_repo_path, 
                              _set_up_test_file, _log_package_info, _log_platform_info)


LOGGER = logging.getLogger(__name__)

REPO_PATH = _recurse_to_repo_path(Path.cwd())
REPO_SRC_DIR = REPO_PATH / "src"
REPO_TESTS_DIR = REPO_PATH / ".tests"
REPO_LOG_FILE = REPO_PATH / "debug.log"


def check_student_code(verbosity: int = 2, logger_level=logging.INFO) -> None:
    """Main check-pfda runner. Outputs results of tests to scripts in `src` to stdout."""
    _init_logger(REPO_LOG_FILE, logger_level)
    current_assignment = get_current_assignment(REPO_PATH, LOGGER)
    if not current_assignment:
        echo("Unable to match chapter and assignment against cwd. Contact your TA.")
        return

    REPO_TESTS_DIR.mkdir(exist_ok=True)

    LOGGER.debug(f"Created/verified .tests directory: {REPO_TESTS_DIR}")

    test_file_path =_set_up_test_file(current_assignment, LOGGER, REPO_TESTS_DIR)
    secho(f"Checking assignment {current_assignment.assignment} at verbosity {verbosity}...", fg="green")
    with _add_to_path(REPO_SRC_DIR):
        _test_student_code(test_file_path, verbosity)


def _init_logger(log_file: Path, log_level):
    if not log_level == logging.DEBUG:
        return
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w'
    )
    _log_platform_info(LOGGER)
    _log_package_info(LOGGER)
    LOGGER.debug(f"Current working directory: {os.getcwd()}")
    LOGGER.debug(f"sys.path: {sys.path}")


def _test_student_code(test_file_path: Path, verbosity: int):
    try:
        args = [str(test_file_path)]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")

        LOGGER.debug(f"Running pytest with args: {args}")

        out = pytest.main(args)
        LOGGER.debug(f"Pytest output:\n{out}")
    except ImportError as e:
        echo(f"Error importing pytest: {e}")
        LOGGER.exception("Failed to import pytest.")
    except PermissionError as e:
        echo(f"Encountered a permission error when trying to access the test file: {e}")
        LOGGER.exception(f"Failed to write test: {e}")
