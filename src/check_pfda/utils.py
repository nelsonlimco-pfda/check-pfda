"""Public modules."""

import logging
import os
import platform
import re
import sys
import time
from contextlib import contextmanager
from importlib import import_module
from importlib.metadata import version as get_installed_version, PackageNotFoundError
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Generator, List, NamedTuple

import click
import pytest
import requests
import yaml

logger = logging.getLogger(__name__)

STRING_LEN_LIMIT = 1000


class AssignmentInfo(NamedTuple):
    """Information about the current assignment.

    ``chapter`` is optional and only ever set by the legacy folder-name
    fallback matcher (see ``_match_assignment_from_config``); it's ``None``
    when the assignment came from an explicit ``.check-pfda.yml`` file,
    since chapter plays no part in that resolution.
    """

    name: str
    chapter: str | None = None


def check_for_updates() -> None:
    """Check PyPI for a newer version and exit with an upgrade prompt if one is available."""
    try:
        installed = get_installed_version("check-pfda")
        r = requests.get("https://pypi.org/pypi/check-pfda/json", timeout=5)
        r.raise_for_status()
        latest = r.json()["info"]["version"]
        installed_tuple = tuple(int(x) for x in installed.split("."))
        latest_tuple = tuple(int(x) for x in latest.split("."))
        if installed_tuple < latest_tuple:
            pip = "pip3" if platform.system() == "Darwin" else "pip"
            click.secho(
                f"\nYour version of check-pfda ({installed}) is out of date. "
                f"The latest version is {latest}.\n"
                f"Please update before continuing:\n\n"
                f"    {pip} install --upgrade check-pfda\n",
                fg="red",
                bold=True,
            )
            sys.exit(1)
    except (PackageNotFoundError, requests.exceptions.RequestException, KeyError, ValueError):
        pass


def assert_script_exists(
    module_name: str, accepted_dirs: list, repo_path: Path
) -> None:
    """Check accepted subfolders for the module script.

    :param module_name: The name of the module to check.
    :type module_name: str
    :param accepted_dirs: The accepted subfolders for the script.
    :type accepted_dirs: list
    :return: None
    :rtype: None
    """
    for subfolder in accepted_dirs:
        filename = repo_path / subfolder / f"{module_name}.py"
        if filename.exists():
            return None
    pytest.fail(
        reason=f"The script '{module_name}.py' does not exist in "
        f"the accepted directories: {accepted_dirs}."
    )


def build_user_friendly_err(actual: Any, expected: Any) -> str:
    """Build a user-friendly error to accompany a pytest AssertionError.

    :param actual: The actual output of the tested program.
    :type actual: Any
    :param expected: The expected output of the tested program.
    :type expected: Any
    :return: A user-friendly error message.
    :rtype: str
    """
    errors = []

    if actual is None and expected is not None:
        errors.append("Your function/program did not produce any output.")
    elif actual is not None and expected is None:
        errors.append("Your function/program produced output when it was not expected.")

    if _is_different_type(expected, actual):
        errors.append(
            f"The expected data type is {_format_type(repr(type(expected)))}, "
            f"but your actual output data type is "
            f"{_format_type(repr(type(actual)))}."
        )
    elif isinstance(expected, str):
        for error in _find_string_comparison_errors(expected, actual):
            errors.append(error)
    else:
        errors.append("Your output does not match the expected format or values.")

    errors_formatted = "\n- ".join(errors)
    error_msg = (
        f"ANGM2305 Autograder User-friendly Message:"
        f"\n--------------------------------------------------------"
        f"\nThe Test Failed."
        f"\n\nWhat the Test Expected:"
        f"\n{expected}"
        f"\n\nWhat your Function/Program output:"
        f"\n{actual}"
        f"\n\nIssues Found:"
        f"\n- {errors_formatted}"
        f"\n\nPytest Error Message:"
        f"\n---------------------"
    )
    return error_msg


class TestFileError(Exception):
    """Raised when there is an error with the test file."""

    pass


ORIGIN_DIR = "dir"        # --dir pointed at this folder
ORIGIN_REPO = "repo"      # found in the repo's own tests/ folder
ORIGIN_REMOTE = "remote"  # downloaded from the tests repo on GitHub


class TestSource(NamedTuple):
    """An assignment's test file, and where it came from."""

    content: str
    origin: str
    path: Path | None


def _find_local_test_file(
    root: Path, chapter: str | None, assignment: str
) -> Path | None:
    """Look for an assignment's test file inside a local directory.

    When a chapter is known, the chaptered layout used historically by
    ``--dir`` (``<root>/c01/test_shout.py``) is checked first, then the flat
    layout (``<root>/test_shout.py``) -- matching the existing precedence
    when both exist. When the chapter is unknown (the assignment was
    resolved via ``.check-pfda.yml``, which carries no chapter), the flat
    layout is checked first, then any ``<root>/cXX/test_shout.py``, so an
    existing chaptered ``--dir`` mirror still works for assignments using the
    new resolution mechanism -- their repo simply doesn't happen to know
    which chapter that mirror filed the test under.

    :param root: The directory to look in.
    :type root: Path
    :param chapter: The chapter number, without its leading 'c', or None.
    :type chapter: str | None
    :param assignment: The assignment name.
    :type assignment: str
    :returns: The path to the test file, or None if no layout matched.
    :rtype: Path | None
    """
    filename = f"test_{assignment}.py"
    candidates = [root / filename]
    if chapter is not None:
        candidates.insert(0, root / f"c{chapter}" / filename)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if chapter is None:
        for chaptered in sorted(root.glob(f"c*/{filename}")):
            if chaptered.is_file():
                return chaptered
    return None


def _read_local_test_file(test_path: Path, assignment: str) -> str:
    """Read and sanity-check a test file that was found on disk.

    :param test_path: The path to the test file.
    :type test_path: Path
    :param assignment: The assignment name, used in messages.
    :type assignment: str
    :returns: The contents of the test file.
    :rtype: str
    :raises TestFileError: If the file is empty.
    """
    content = test_path.read_text(encoding="utf-8")
    if not content.strip():
        click.secho(
            "Error: Local test file is empty. Contact your instructor.",
            fg="red",
            bold=True,
        )
        logger.error(
            f"Error: Empty local test file for assignment '{assignment}'."
        )
        raise TestFileError(
            f"Error: Received empty test file for assignment '{assignment}'."
        )
    if "def test_" not in content:
        click.secho("Warning: This may not be a valid test file.", fg="yellow")
        logger.warning(
            f"Warning: This may not be a valid test file for assignment "
            f"'{assignment}'."
        )
    return content


def _fetch_remote_tests(assignment: str) -> str:
    """Download an assignment's test file from the remote tests repository.

    The remote tests repository is a single flat namespace
    (``test_<assignment>.py``), not chaptered -- chapter plays no part in
    finding a test remotely.

    :param assignment: The assignment name.
    :type assignment: str
    :returns: The contents of the test file.
    :rtype: str
    :raises TestFileError: If the download fails or returns an empty file.
    """
    tests_repo_url = _construct_test_url(assignment)
    try:
        r = requests.get(tests_repo_url, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        click.secho(
            f"Error fetching test file for assignment '{assignment}': {e}",
            fg="red",
            bold=True,
        )
        logger.exception(f"Error fetching test file for assignment '{assignment}': {e}")
        raise TestFileError(
            f"Error fetching test file for assignment '{assignment}': {e}"
        )

    if not r.text.strip():
        click.secho(
            "Error: Received empty test file. Contact your instructor.",
            fg="red",
            bold=True,
        )
        logger.error(
            f"Error: Received empty test file for assignment '{assignment}'."
        )
        raise TestFileError(
            f"Error: Received empty test file for assignment '{assignment}'."
        )

    if "def test_" not in r.text:
        click.secho("Warning: This may not be a valid test file.", fg="yellow")
        logger.warning(
            f"Warning: This may not be a valid test file for assignment '{assignment}'."
        )
    return r.text


def resolve_tests(
    chapter: str | None,
    assignment: str,
    local_tests_root: Path | None = None,
    repo_path: Path | None = None,
    force_remote: bool = False,
) -> TestSource:
    """Get tests for a given assignment, and report where they came from.

    Sources are tried in order: the directory given by ``--dir``, then the
    repository's own ``tests`` directory, then the remote tests repository. An
    explicit ``--dir`` beats auto-detection, and a missing file there is an
    error rather than a fallback, since the flag states an intent. Whenever
    tests come from somewhere other than the remote repository, the file being
    used is announced.

    ``chapter`` only affects the local sources -- it lets ``--dir``/the
    repo's own ``tests`` directory be organized into chaptered subfolders,
    for backward compatibility with existing local mirrors. It's ``None``
    when the assignment was resolved via ``.check-pfda.yml``, in which case
    the flat local layout is checked first, falling back to any chaptered
    subfolder found on disk. The remote tests repository is a single flat
    namespace regardless, so ``chapter`` plays no part there.

    :param chapter: The chapter number, without its leading 'c', or None.
    :type chapter: str | None
    :param assignment: The assignment name.
    :type assignment: str
    :param local_tests_root: Directory given by ``--dir``, if any.
    :type local_tests_root: Path | None
    :param repo_path: The assignment repository root, checked for a ``tests``
        directory.
    :type repo_path: Path | None
    :param force_remote: Skip both on-disk sources and download the tests.
    :type force_remote: bool
    :returns: The test file contents and the source they came from.
    :rtype: TestSource
    :raises TestFileError: If tests cannot be obtained from the chosen source.
    """
    if force_remote:
        return TestSource(_fetch_remote_tests(assignment), ORIGIN_REMOTE, None)

    if local_tests_root is not None:
        test_path = _find_local_test_file(local_tests_root, chapter, assignment)
        if test_path is None:
            expected = f"<dir>/test_{assignment}.py"
            if chapter is not None:
                expected = f"<dir>/c{chapter}/test_{assignment}.py or {expected}"
            msg = f"Local test file not found under {local_tests_root}. Expected {expected}"
            click.secho(msg, fg="red", bold=True)
            logger.error(msg)
            raise TestFileError(msg)
        click.secho(f"Using tests from --dir: {test_path}", fg="yellow")
        return TestSource(
            _read_local_test_file(test_path, assignment), ORIGIN_DIR, test_path
        )

    if repo_path is not None:
        test_path = _find_local_test_file(repo_path / "tests", chapter, assignment)
        if test_path is not None:
            click.secho(
                f"Using the local tests in this repository: "
                f"{test_path.relative_to(repo_path)} "
                f"(not the remote tests).",
                fg="yellow",
            )
            return TestSource(
                _read_local_test_file(test_path, assignment), ORIGIN_REPO, test_path
            )

    return TestSource(_fetch_remote_tests(assignment), ORIGIN_REMOTE, None)


def get_tests(
    chapter: str | None,
    assignment: str,
    local_tests_root: Path | None = None,
    repo_path: Path | None = None,
) -> str:
    """Get tests for a given assignment.

    :param chapter: The chapter number, without its leading 'c', or None if
        unknown -- only affects chaptered local ``--dir`` layouts; the
        remote tests repository is a flat namespace.
    :type chapter: str | None
    :param assignment: The assignment name.
    :type assignment: str
    :param local_tests_root: Directory given by ``--dir``, if any.
    :type local_tests_root: Path | None
    :param repo_path: The assignment repository root, checked for a ``tests``
        directory.
    :type repo_path: Path | None
    :returns: The contents of the test file.
    :rtype: str
    """
    return resolve_tests(
        chapter, assignment, local_tests_root, repo_path
    ).content


def reload_module(module_name: str) -> None:
    """Reload the module. Ensures it is reloaded if previously loaded.

    :param module_name: The name of the module to reload.
    :type module_name: str
    """
    sys.modules.pop(module_name, None)
    import_module(name=module_name)


def patch_input_output(
    monkeypatch: Any, test_inputs: list, module_name: str
) -> StringIO:
    """Patch input() and standard out.

    :param monkeypatch: Pytest's monkeypatch fixture.
    :type monkeypatch: Any
    :param test_inputs: The inputs to test known outputs against.
    :type test_inputs: list
    :param module_name: The name of the module to test.
    :type module_name: str
    :return: The patched standard out.
    :rtype: StringIO
    """
    # patches the standard output to catch the output of print()
    patch_stdout = StringIO()
    # Returns a new mock object which undoes any patching done inside
    # the with block on exit to avoid breaking pytest itself.
    with monkeypatch.context() as m:
        # patches the input()
        m.setattr("builtins.input", lambda _: test_inputs.pop(0))
        m.setattr("sys.stdout", patch_stdout)
        reload_module(module_name)
    return patch_stdout


"""
Private functions. Do not implement these directly in any unit tests.
"""


def _format_type(var_type: str) -> str:
    """Format repr class type to make <class 'xyz'> more readable.

    :param var_type: The string representation of a type (e.g., "<class 'str'>").
    :type var_type: str
    :return: The formatted type name (e.g., "str") or an error message if var_type is empty.
    :rtype: str
    """
    if not var_type:
        return "Your function output None, but is expected to return a value."

    parts_split_on_quotes = var_type.split("'")
    class_name = parts_split_on_quotes[1::2]
    return class_name[0] if class_name else var_type


def _is_different_type(expected: Any, actual: Any) -> bool:
    """Evaluate if the two arguments are the same type.

    :param expected: The expected object.
    :type expected: Any
    :param actual: The actual object.
    :type actual: Any
    :return: If the two objects are the same type.
    :rtype: bool
    """
    return not isinstance(actual, type(expected))


def _find_string_comparison_errors(expected: str, actual: str) -> list:
    """Handle string comparison for asserting equivalency.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: An error message.
    :rtype: list
    """
    errors = []
    expected_len = len(expected)
    actual_len = len(actual)
    # Enforce a length limit in case a student accidentally makes
    # an enormous string.
    check_length_error_msg = _check_length_limit(actual, STRING_LEN_LIMIT)
    if check_length_error_msg:
        errors.append(check_length_error_msg)
        return errors
    check_functions = [_check_trailing_newline, _check_double_spaces]
    for f in check_functions:
        if f(expected, actual):
            errors.append(f(expected, actual))
    # Highlight which character differs.
    if expected_len == actual_len:
        errors.append(_find_incorrect_char(expected, actual))
    # Else highlight the length difference.
    else:
        errors.append(
            f"The expected and actual string lengths are "
            f"different. Expected length: {expected_len}, but "
            f"got length: {actual_len}."
        )
    return errors


def _find_incorrect_char(expected: str, actual: str) -> str:
    """Find the index of the first actual char that doesn't match expected.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: A string containing the incorrect character and its index.
    :rtype: str
    """
    for idx, expected_char in enumerate(expected):
        actual_char = actual[idx]
        if expected_char != actual_char:
            return (
                f"Character '{actual[idx]}' at index {idx} does "
                f"not match with the expect output. "
                f"This is the first mismatched character. There "
                f"may be others."
            )


def _check_trailing_newline(expected: str, actual: str) -> str | None:
    """Check the actual string for common errors.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: A string to concatenate to the error if there are
        common errors, otherwise None.
    :rtype: str | None
    """
    if actual.endswith("\n") and not expected.endswith("\n"):
        return (
            "Your program/function's output has an extra newline "
            "character '\\n' at the end."
        )


def _check_double_spaces(expected: str, actual: str) -> str | None:
    """Check the actual string for double spaces.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: A string to concatenate to the error if there are
        common errors, otherwise None.
    :rtype: str | None
    """
    if "  " in actual and "  " not in expected:
        return (
            f"There are two spaces at index {actual.index('  ')} "
            f"of your program/function's output."
        )


def _check_length_limit(actual: str, limit: int) -> str | None:
    """Enforce a length limit on the actual string.

    :param actual: The actual string.
    :type actual: str
    :param limit: The expected length.
    :type limit: int
    :return: A string to concatenate to the error if there are
        common errors, otherwise None.
    :rtype: str | None
    """
    actual_len = len(actual)
    if actual_len > limit:
        return (
            f"The actual string exceeds the maximum allowed "
            f"length.\n Actual length is: {actual_len}\n"
            f"Limit is: {limit}"
        )


def _construct_test_url(assignment: str) -> str:
    """Construct the URL at which the test lives.

    The remote tests repository is a single flat namespace
    (``test_<assignment>.py``), not chaptered -- chapter plays no part in
    finding a test remotely.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "check_pfda", "config.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    base_url = config["tests"]["tests_repo_url"]

    # query at the end forces CDN to flush cache
    return f"{base_url}/test_{assignment}.py?now={int(time.time())}"


def _load_config_yaml() -> dict | None:
    """Load and parse the YAML configuration file.

    :return: The parsed YAML config dictionary, or None if loading/parsing failed.
    :rtype: dict | None
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "check_pfda", "config.yaml")
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        logger.exception(f"YAML file not found: {config_path}")
        return None
    except yaml.YAMLError as e:
        logger.exception(f"Error parsing YAML file: {e}")
        return None


def _tokenize(text: str) -> List[str]:
    """Split text into lowercase tokens on ``-``/``_`` boundaries.

    Used to compare folder-name components as whole words rather than raw
    substrings, so e.g. a username like ``leshoutier`` doesn't accidentally
    contain the assignment name ``shout``.

    :param text: The text to tokenize.
    :type text: str
    :returns: The non-empty tokens, lowercased.
    :rtype: List[str]
    """
    return [t for t in re.split(r"[-_]", text.lower()) if t]


def _find_subsequence_starts(tokens: List[str], sub: List[str]) -> List[int]:
    """Find every index where ``sub`` occurs as a contiguous run within ``tokens``.

    :param tokens: The tokens to search.
    :type tokens: List[str]
    :param sub: The token sequence to look for.
    :type sub: List[str]
    :returns: Every starting index of a match, in ascending order.
    :rtype: List[int]
    """
    n = len(sub)
    return [i for i in range(len(tokens) - n + 1) if tokens[i:i + n] == sub]


class CheckFileError(Exception):
    """Raised when a repo's ``.check-pfda.yml`` exists but is invalid."""

    pass


_CHECK_FILE_NAME = ".check-pfda.yml"


def _read_check_file(repo_path: Path) -> str | None:
    """Read the assignment name declared by a repo's ``.check-pfda.yml``, if any.

    This is the authoritative source of assignment identity: a repo that has
    this file is trusted completely, with no folder-name parsing involved at
    all. Absence is a normal, expected case (older repos predate this file)
    and simply means the caller should fall back to folder-name detection --
    but a file that *exists* and is broken is an authoring mistake that
    should be surfaced immediately rather than silently masked by a fallback
    match.

    :param repo_path: The path to the repository root.
    :type repo_path: Path
    :returns: The declared assignment name, or None if no ``.check-pfda.yml`` exists.
    :rtype: str | None
    :raises CheckFileError: If the file exists but can't be parsed, or has no
        ``assignment`` value.
    """
    check_path = repo_path / _CHECK_FILE_NAME
    if not check_path.is_file():
        return None

    try:
        data = yaml.safe_load(check_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise CheckFileError(f"Couldn't parse {_CHECK_FILE_NAME}: {e}") from e

    if not isinstance(data, dict):
        raise CheckFileError(
            f"{_CHECK_FILE_NAME} must be a YAML mapping with an 'assignment' key."
        )

    assignment = str(data.get("assignment") or "").strip()
    if not assignment:
        raise CheckFileError(
            f"{_CHECK_FILE_NAME} is missing an 'assignment' value."
        )
    return assignment


def get_current_assignment(repo_path: Path) -> AssignmentInfo | None:
    """
    Determines the current assignment, preferring an explicit
    ``.check-pfda.yml`` declaration and falling back to matching the
    repository's own folder name against a YAML configuration file.

    Only the folder name itself is checked in the fallback (not the rest of
    the path), since that's the only part of the path the assignment-
    detection convention makes any promise about -- an ancestor directory
    (e.g. a parent folder that happens to be named after a chapter or
    assignment) plays no part.

    :param repo_path: The path to the repository root.
    :type repo_path: Path

    :return: An AssignmentInfo named tuple if found, None on error
    :rtype: AssignmentInfo | None
    """
    # Note that we use click.secho, not classic print, to show terminal output.
    try:
        declared_assignment = _read_check_file(repo_path)
    except CheckFileError as e:
        click.secho(
            f"Error in {_CHECK_FILE_NAME}: {e} Contact your TA.",
            fg="red",
            bold=True,
        )
        logger.error(f"Invalid {_CHECK_FILE_NAME} in {repo_path}: {e}")
        return None

    if declared_assignment is not None:
        result = AssignmentInfo(name=declared_assignment)
        logger.debug(f"Current assignment info (from {_CHECK_FILE_NAME}): {result}")
        return result

    # TODO: this shouldn't be in business logic--this should be refactored such that
    # if an assignment is not found, it returns None and the caller can handle it accordingly.
    # Likely that means printing a message that says "This assignment doesn't have any tests! Check the README
    # for more information."
    repo_name = repo_path.name
    tokens = _tokenize(repo_name)
    if "c07" in tokens or "c08" in tokens:
        click.secho(
            "C07 and C08 do not have any automated tests. Refer to the README for more information.",
            fg="yellow",
        )
        return None

    config = _load_config_yaml()
    if config is None:
        return None

    logger.debug(
        f"No {_CHECK_FILE_NAME} found in {repo_path}; falling back to folder-name detection."
    )
    return _match_assignment_from_config(config, repo_name)


def _match_assignment_from_config(
    config: dict, repo_name: str
) -> AssignmentInfo | None:
    """Match the repository's folder name against the config to find the current assignment.

    This logic is necessary because there's no way to get the name of the current assignment without some
    external source of assignment names from the student's repo's root dir. This is because assignment names
    vary in length and student names also vary in length and both may use the same delimiter. For example:

    pfda-c01-lab-favorite-artist-bencres-demo

    and

    pfda-c01-lab-shout-bencres-demo

    In this case, we can't get 'favorite-artist' or 'shout' without knowing at least one of:

    1. The student's GitHub username.
    2. Names of valid assignments.

    Matching is done on whole, hyphen/underscore-delimited tokens rather than
    raw substrings, so a username like ``leshoutier`` can't be mistaken for
    the assignment ``shout``. When more than one assignment's tokens are
    found in the folder name (e.g. a username of ``shout-master`` on a
    ``favorite-artist`` repo), the one whose tokens start closest to the
    chapter marker wins, since GitHub Classroom always appends the username
    as a trailing suffix -- the real assignment name can never start later in
    the folder name than any part of the username.

    :param config: The parsed YAML configuration dictionary.
    :type config: dict
    :param repo_name: The repository's own folder name (not the full path).
    :type repo_name: str
    :return: An AssignmentInfo named tuple if a match is found, None otherwise.
    :rtype: AssignmentInfo | None
    """
    tokens = _tokenize(repo_name)

    # (start index, -token length, chapter_key, assignment) for every match,
    # so sorting favors the earliest, then longest (most specific) match.
    candidates = []
    for chapter_key, assignments in config.get("tests", {}).items():
        # Skip the tests_repo_url key
        if chapter_key == "tests_repo_url":
            continue
        if chapter_key not in tokens:
            continue
        chapter_idx = tokens.index(chapter_key)
        for assignment in assignments:
            assignment_tokens = _tokenize(assignment)
            for start in _find_subsequence_starts(tokens, assignment_tokens):
                if start <= chapter_idx:
                    continue  # the assignment name must follow the chapter marker
                candidates.append(
                    (start, -len(assignment_tokens), chapter_key, assignment)
                )

    if not candidates:
        # No match found
        logger.debug("Error parsing cwd and matching it against config. Contact your TA.")
        logger.debug(f"Config: {config}")
        logger.debug(f"Repo folder name: {repo_name}")
        return None

    candidates.sort()
    distinct_matches = {(c[2], c[3]) for c in candidates}
    if len(distinct_matches) > 1:
        logger.warning(
            f"Ambiguous assignment match for repo folder {repo_name!r}: "
            f"{sorted(distinct_matches)}. Using the match closest to the "
            f"chapter marker: {candidates[0][2:]}"
        )

    _, _, chapter_key, assignment = candidates[0]
    result = AssignmentInfo(
        chapter=str(chapter_key)[1:], name=str(assignment).replace("-", "_")
    )
    logger.debug(f"Current assignment info: {result}")
    return result


class RepositoryNotFound(Exception):
    """Raised when the repository root cannot be located."""

    pass


def _has_git_entry(path: Path) -> bool:
    """Check whether ``path`` holds a ``.git`` entry, marking it a repo root.

    Usually ``.git`` is a directory. In worktrees and submodules it is instead
    a file holding a single ``gitdir: <path>`` line pointing at the real git
    data, so a directory-only check would walk past those roots. The contents
    are verified rather than trusting the name alone, so an unrelated file that
    happens to be called ``.git`` is not mistaken for a repository root.

    :param path: The directory to check.
    :type path: Path
    :returns: True if the directory holds a git directory or pointer file.
    :rtype: bool
    """
    git_path = path / ".git"
    if git_path.is_dir():
        return True
    if not git_path.is_file():
        return False
    try:
        return git_path.read_text(encoding="utf-8").startswith("gitdir:")
    except OSError as e:
        logger.debug(f"Could not read {git_path}: {e}")
        return False
    except UnicodeDecodeError:
        logger.debug(f"{git_path} is not a readable git pointer file.")
        return False


def _has_repo_doc_files(path: Path) -> bool:
    """Check whether ``path`` holds both a ``README.md`` and a ``.gitignore``.

    Fallback for repositories handed out without a ``.git`` directory, such as a
    zip download. Both files are required: a lone ``README.md`` appears in
    subdirectories often enough to cause false positives on its own.

    :param path: The directory to check.
    :type path: Path
    :returns: True if both files exist in the directory.
    :rtype: bool
    """
    return (path / "README.md").is_file() and (path / ".gitignore").is_file()


def _recurse_to_repo_path(current_path: Path) -> Path:
    """Recursively search upward for the assignment repository's root directory.

    Runs two separate passes: first looking for a ``.git`` entry, then falling
    back to a ``README.md`` + ``.gitignore`` pair. Separate passes matter
    because students often run from inside a subdirectory such as ``src``. If
    that subdirectory happens to hold a README and a gitignore, a combined
    check would stop there even though the real root above it has a ``.git``.
    Two passes let the stronger signal win regardless of which directory is
    nearer.

    :param current_path: The starting path to search upward from.
    :type current_path: Path
    :returns: The path to the repository root.
    :rtype: Path
    :raises RepositoryNotFound: If no repository root is found up to root.
    """
    searched_paths: List[Path] = []
    for is_repo_root in (_has_git_entry, _has_repo_doc_files):
        searched_paths = []
        found = _recurse_to_repo_path_helper(
            current_path, searched_paths, is_repo_root
        )
        if found is not None:
            return found

    path_list = "\n  ".join(str(p) for p in searched_paths)
    raise RepositoryNotFound(
        f"No repository root found starting from {searched_paths[0]!s}.\n"
        f"Looked for a '.git' entry, then for a 'README.md' and "
        f"'.gitignore' pair.\n"
        f"Searched paths:\n  {path_list}"
    )


def _recurse_to_repo_path_helper(
    current_path: Path,
    searched_paths: List[Path],
    is_repo_root: Callable[[Path], bool],
) -> Path | None:
    """Helper function that recursively searches upward and collects searched paths.

    :param current_path: The current path being checked.
    :type current_path: Path
    :param searched_paths: List to accumulate all paths that were searched.
    :type searched_paths: List[Path]
    :param is_repo_root: Predicate deciding whether a directory is the root.
    :type is_repo_root: Callable[[Path], bool]
    :returns: The repository root, or None if the filesystem root was reached.
    :rtype: Path | None
    """
    searched_paths.append(current_path)

    if is_repo_root(current_path):
        return current_path

    # filesystem root
    if current_path.parent == current_path:
        return None

    return _recurse_to_repo_path_helper(
        current_path.parent, searched_paths, is_repo_root
    )


def _set_up_test_file(
    assignment: AssignmentInfo,
    repo_tests_dir: Path,
    local_tests_root: Path | None = None,
    repo_path: Path | None = None,
    force_remote: bool = False,
) -> tuple[Path, TestSource]:
    """Return the test file to run pytest against, fetching it if needed.

    A local source (found via ``--dir`` or the repository's own ``tests``
    directory) is run in place, from wherever it already lives on disk.
    Only the remote fallback needs an isolated copy -- there's no other file
    on disk to point pytest at -- which is what ``repo_tests_dir`` (the
    ``.tests`` directory) is for. It's created lazily, only when that copy is
    actually written.

    :param assignment: The chapter and name of the assignment being checked.
    :type assignment: AssignmentInfo
    :param repo_tests_dir: Where to cache a downloaded test file, if needed.
    :type repo_tests_dir: Path
    :param local_tests_root: Directory given by ``--dir``, if any.
    :type local_tests_root: Path | None
    :param repo_path: The assignment repository root.
    :type repo_path: Path | None
    :param force_remote: Skip both on-disk sources and download the tests.
    :type force_remote: bool
    :returns: The test file to run, and where it came from.
    :rtype: tuple[Path, TestSource]
    """
    chapter = assignment.chapter
    assignment_name = assignment.name
    logger.debug(f"Chapter: {chapter}, Assignment: {assignment}")
    source = resolve_tests(
        chapter, assignment_name, local_tests_root, repo_path, force_remote
    )
    if source.path is not None:
        return source.path, source

    repo_tests_dir.mkdir(exist_ok=True)
    logger.debug(f"Created/verified .tests directory: {repo_tests_dir}")
    test_file_path = repo_tests_dir / f"test_{assignment_name}.py"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(source.content)
    logger.debug(f"Wrote test file to: {test_file_path}")
    return test_file_path, source


# Directory names that never hold student code. Dot-prefixed directories are
# skipped separately, which covers .git, .tests and .venv. 'tests' and 'test'
# are excluded so a repository's own test file -- which _set_up_test_file()
# may run directly out of that directory, see _find_local_test_file -- isn't
# mistaken for importable student code.
_SKIPPED_DIR_NAMES = frozenset(
    {"tests", "test", "__pycache__", "node_modules", "site-packages"}
)


def _is_skipped_dir(path: Path) -> bool:
    """Check whether a directory should be excluded when looking for student code.

    :param path: The directory to check.
    :type path: Path
    :returns: True if the directory should be skipped.
    :rtype: bool
    """
    if path.name.startswith(".") or path.name in _SKIPPED_DIR_NAMES:
        return True
    # Identifies a virtual environment by what it contains, not by its name.
    return (path / "pyvenv.cfg").is_file()


def find_student_code_dirs(repo_path: Path) -> List[Path]:
    """Find the directories in a repository that hold student code.

    The repository root is always included. Beyond that, any directory
    holding at least one ``.py`` file qualifies. Student code is therefore
    importable wherever it lives, rather than only from a hardcoded ``src``
    directory.

    :param repo_path: The path to the repository root.
    :type repo_path: Path
    :returns: Directories to place on ``sys.path``, shallowest first.
    :rtype: list[Path]
    """
    found = {repo_path}

    def walk(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except OSError as e:
            logger.debug(f"Could not read directory {directory}: {e}")
            return
        for entry in entries:
            if not entry.is_dir() or _is_skipped_dir(entry):
                continue
            if any(entry.glob("*.py")):
                found.add(entry)
            walk(entry)

    walk(repo_path)
    ordered = sorted(
        found, key=lambda p: (len(p.relative_to(repo_path).parts), str(p))
    )
    logger.debug(f"Student code directories: {[str(p) for p in ordered]}")
    return ordered


@contextmanager
def _add_to_path(
    paths: str | Path | List[str | Path],
) -> Generator[None, None, None]:
    """Temporarily add one or more directories to sys.path.

    Accepts a single directory or a list of them. Directories end up in
    ``sys.path`` in the order given, so the caller's ordering is the import
    search order. Any directory already on ``sys.path`` is left alone and is
    not removed afterwards. Whatever happens inside the block, ``sys.path``
    is restored.

    :param paths: A directory, or a list of directories in the order they
        should be searched.
    :type paths: str | Path | List[str | Path]
    :yields: None. Used only to bracket the block where the paths are on
        ``sys.path``.
    :ytype: None
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    added = []
    # Reversed because each insert goes to the front, so the first directory
    # given is inserted last and therefore ends up first in the search order.
    for path in reversed(paths):
        resolved = str(Path(path).resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)
            added.append(resolved)
    try:
        yield
    finally:
        for resolved in added:
            if resolved in sys.path:
                sys.path.remove(resolved)


def _log_platform_info():
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Python executable: {sys.executable}")
    logger.debug(f"Platform: {platform.platform()}")
    logger.debug(f"System: {platform.system()} {platform.release()}")
    logger.debug(f"Machine: {platform.machine()}")
    logger.debug(f"Processor: {platform.processor()}")


def _log_package_info():
    logger.debug(f"Installed packages:")
    try:
        import pkg_resources

        installed_packages = [
            (d.project_name, d.version) for d in pkg_resources.working_set
        ]
        installed_packages.sort()
        for package_name, version in installed_packages:
            logger.debug(f"  {package_name}=={version}")
    except ImportError as e:
        logger.debug(f"Unable to retrieve package information: {e}")
