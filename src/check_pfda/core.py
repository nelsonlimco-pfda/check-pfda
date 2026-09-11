"""Collect tests and run them on supplied code."""

import logging
import os
import sys
from pathlib import Path

import pytest
from click import Abort, confirm, echo, secho

from check_pfda.utils import (
    ORIGIN_REPO,
    AssignmentInfo,
    RepositoryNotFound,
    TestFileError,
    TestSource,
    _add_to_path,
    _log_package_info,
    _log_platform_info,
    _recurse_to_repo_path,
    _set_up_test_file,
    check_for_updates,
    find_student_code_dirs,
    get_current_assignment,
    resolve_tests,
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
    force_remote: bool = False,
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

    test_file_path, source = _set_up_test_file(
        current_assignment, repo_tests_dir, tests_dir, repo_path, force_remote
    )
    secho(
        f"Checking chapter {current_assignment.chapter} assignment "
        f"{current_assignment.name} at verbosity {verbosity}...",
        fg="green",
    )
    with _add_to_path(find_student_code_dirs(repo_path)):
        exit_code = _test_student_code(test_file_path, verbosity)
        if exit_code:
            _offer_remote_trial(
                current_assignment, repo_tests_dir, source, verbosity
            )


def _offer_remote_trial(
    assignment: AssignmentInfo,
    repo_tests_dir: Path,
    source: TestSource,
    verbosity: int,
) -> None:
    """After a failure, offer to run the remote tests instead.

    Only offered for tests the tool found by itself in the repository's
    tests/ folder. A student who passed --dir picked that folder on purpose,
    so it is left alone.

    :param assignment: The chapter and name of the assignment being checked.
    :type assignment: AssignmentInfo
    :param repo_tests_dir: The .tests directory to write the trial into.
    :type repo_tests_dir: Path
    :param source: Where the tests that just ran came from.
    :type source: TestSource
    :param verbosity: How many -v flags to pass to pytest.
    :type verbosity: int
    """
    if source.origin != ORIGIN_REPO:
        return

    if not sys.stdin.isatty():
        secho(
            "\nThose were the local tests in this repository. To try the "
            "remote tests instead, run again with --remote.",
            fg="yellow",
        )
        return

    secho(
        "\nThose were the local tests in this repository's tests/ folder, "
        "which may be out of date.",
        fg="yellow",
    )
    try:
        if not confirm("Try the remote tests instead?", default=True):
            return
    except Abort:
        echo()
        return

    try:
        remote = resolve_tests(
            assignment.chapter, assignment.name, force_remote=True
        )
    except TestFileError:
        # resolve_tests has already explained what went wrong.
        return

    # Deliberately not the filename the first run used. Pytest reuses a module
    # it has already imported, so writing over that file would silently run
    # the local tests again.
    trial_path = repo_tests_dir / f"test_{assignment.name}_remote.py"
    trial_path.write_text(remote.content, encoding="utf-8")

    secho("\nTrial run using the remote tests.", fg="green")
    _test_student_code(trial_path, verbosity)


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


def _test_student_code(test_file_path: Path, verbosity: int) -> int | None:
    """Run pytest against a test file.

    :param test_file_path: The test file to run.
    :type test_file_path: Path
    :param verbosity: How many -v flags to pass to pytest.
    :type verbosity: int
    :returns: Pytest's exit code, or None if pytest could not be run.
    :rtype: int | None
    """
    try:
        args = [str(test_file_path)]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")

        LOGGER.debug(f"Running pytest with args: {args}")

        out = pytest.main(args)
        LOGGER.debug(f"Pytest output:\n{out}")
        return int(out)
    except ImportError as e:
        echo(f"Error importing pytest: {e}")
        LOGGER.exception("Failed to import pytest.")
    except PermissionError as e:
        echo(f"Encountered a permission error when trying to access the test file: {e}")
        LOGGER.exception(f"Failed to write test: {e}")
    return None
