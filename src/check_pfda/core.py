"""Collect tests and run them on supplied code."""

import logging
import os
import sys
from pathlib import Path

import pytest
from click import echo, secho

from check_pfda.utils import (
    RepositoryNotFound,
    _add_to_path,
    _log_package_info,
    _log_platform_info,
    _recurse_to_repo_path,
    _set_up_test_file,
    check_for_updates,
    get_current_assignment,
)


LOGGER = logging.getLogger(__name__)

# Compatibility shim: the downloaded autograder tests do
# `from check_pfda.core import REPO_PATH`, so this name has to exist as a
# module attribute by the time pytest imports them. It stays None until a
# check_student_code() run actually locates a repository, so importing this
# module never triggers the filesystem lookup on its own.
REPO_PATH: Path | None = None


def check_student_code(
    verbosity: int = 2,
    logger_level=logging.INFO,
    tests_dir: Path | None = None,
) -> None:
    """Run the checker: outputs results of the assignment's tests to stdout."""
    check_for_updates()

    # Looked up here rather than at import time, so a missing repository is
    # reported as a message instead of a traceback raised during import.
    try:
        repo_path = _recurse_to_repo_path(Path.cwd())
    except RepositoryNotFound as e:
        secho(
            "Couldn't find your assignment repository. Make sure you're "
            "running this from inside your assignment folder.",
            fg="red",
            bold=True,
        )
        LOGGER.debug(f"Repository lookup failed: {e}")
        return

    global REPO_PATH
    REPO_PATH = repo_path

    repo_tests_dir = repo_path / ".tests"
    _init_logger(repo_path / "debug.log", logger_level)
    LOGGER.debug(f"Repository root: {repo_path}")

    current_assignment = get_current_assignment(repo_path)
    if not current_assignment:
        echo("Unable to match chapter and assignment against cwd. Contact your TA.")
        return

    repo_tests_dir.mkdir(exist_ok=True)

    LOGGER.debug(f"Created/verified .tests directory: {repo_tests_dir}")

    test_file_path = _set_up_test_file(current_assignment, repo_tests_dir, tests_dir)
    secho(
        f"Checking chapter {current_assignment.chapter} assignment "
        f"{current_assignment.name} at verbosity {verbosity}...",
        fg="green",
    )
    with _add_to_path(repo_path / "src"):
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
    _log_platform_info()
    _log_package_info()
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
