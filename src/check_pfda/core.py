"""Collect tests and run them on supplied code."""

import os
from pathlib import Path
import sys
import logging
import platform


from click import echo
import pytest
from check_pfda.utils import get_current_assignment, get_tests, _add_src_to_sys_path, _remove_src_from_sys_path, _recurse_to_repo_path


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
    chapter = current_assignment.chapter
    assignment = current_assignment.assignment
    echo(f"Checking assignment {assignment} at verbosity {verbosity}...")

    LOGGER.debug(f"Chapter: {chapter}, Assignment: {assignment}")

    tests = get_tests(chapter, assignment)
    LOGGER.debug(f"Retrieved tests (length: {len(tests)} bytes)")

    REPO_TESTS_DIR.mkdir(exist_ok=True)

    LOGGER.debug(f"Created/verified .tests directory: {REPO_TESTS_DIR}")

    # Write test file to .tests directory
    test_file_path = REPO_TESTS_DIR / f"test_{assignment}.py"

    _add_src_to_sys_path(src_path, debug, LOGGER)
    _pytest_student_code(debug, test_file_path, tests, verbosity)
    _remove_src_from_sys_path(debug, src_path, LOGGER)


def _init_logger(log_file: Path, log_level):
    if not log_level == logging.DEBUG:
        return
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w'
    )
    _log_platform_info()
    _log_package_info()
    LOGGER.debug(f"Current working directory: {os.getcwd()}")
    LOGGER.debug(f"sys.path: {sys.path}")


def _log_platform_info():
    LOGGER.debug(f"Python version: {sys.version}")
    LOGGER.debug(f"Python executable: {sys.executable}")
    LOGGER.debug(f"Platform: {platform.platform()}")
    LOGGER.debug(f"System: {platform.system()} {platform.release()}")
    LOGGER.debug(f"Machine: {platform.machine()}")
    LOGGER.debug(f"Processor: {platform.processor()}")


def _log_package_info():
    LOGGER.debug(f"Installed packages:")
    try:
        import pkg_resources
        installed_packages = [(d.project_name, d.version) for d in pkg_resources.working_set]
        installed_packages.sort()
        for package_name, version in installed_packages:
            LOGGER.debug(f"  {package_name}=={version}")
    except Exception as e:
        LOGGER.debug(f"Unable to retrieve package information: {e}")


def _pytest_student_code(debug: bool, test_file_path: Path, tests, verbosity: int):
    try:
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(tests)

        LOGGER.debug(f"Wrote test file to: {test_file_path}")

        args = [str(test_file_path)]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")

        LOGGER.debug(f"Running pytest with args: {args}")

        out = pytest.main(args)
        LOGGER.debug(f"Pytest output: {out}")
    except Exception as e:
        echo(f"Error writing or running test file: {e}")
        LOGGER.exception("Failed to write or run test file")
