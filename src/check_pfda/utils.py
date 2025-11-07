"""Public modules."""
import os
import sys
from importlib import import_module
from io import StringIO
from pathlib import Path
from typing import Any

import click

import py.path

import pytest

import requests

import yaml

# Constants.
STRING_LEN_LIMIT = 1000


"""
Public functions. These are intended for direct implementation in unit tests.
"""


def assert_script_exists(module_name: str, accepted_dirs: list) -> None:
    """Check accepted subfolders for the module script.

    :param module_name: The name of the module to check.
    :type module_name: str
    :param accepted_dirs: The accepted subfolders for the script.
    :type accepted_dirs: list
    :return: None
    :rtype: None
    """
    current_path = Path.cwd()
    if current_path.name == "src":
        current_path = current_path.parent
    for subfolder in accepted_dirs:
        filename = current_path / subfolder / f"{module_name}.py"
        if filename.exists():
            return None
    pytest.fail(reason=f"The script '{module_name}.py' does not exist in "
                       f"the accepted directories: {accepted_dirs}.")


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
        errors.append("Your function/program produced output when it was "
                      "not expected.")

    if _is_different_type(expected, actual):
        errors.append(
            f"The expected data type is {_format_type(type(expected))}, "
            f"but your actual output data type is "
            f"{_format_type(type(actual))}.")
    elif isinstance(expected, str):
        for error in _find_string_comparison_errors(expected, actual):
            errors.append(error)
    else:
        errors.append("Your output does not match the expected "
                      "format or values.")

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
        f"\n---------------------")
    return error_msg


def generate_temp_file(filename: str,
                       tmpdir: py.path.local,
                       contents: Any) -> str:
    """Generate a temporary file to test with.

    :param filename: The name of the temporary file.
    :type filename: str
    :param tmpdir: Pytest's tmpdir fixture.
    :type tmpdir: py.path.local
    :param contents: The contents to write to the temporary file.
    :type contents: Any
    :return: The path to the temporary file.
    :rtype: str
    """
    filepath = os.path.join(tmpdir, filename)
    with open(filepath, "w") as f:
        f.write(contents)
    return filepath


def get_tests(chapter, assignment: str) -> str:
    """Get tests for a given assignment."""
    tests_repo_url = _construct_test_url(chapter, assignment)
    try:
        r = requests.get(tests_repo_url, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        click.secho(f"Error fetching test file for assignment '"
                    f"{assignment}': {e}", fg="red", bold=True)
        sys.exit(1)

    if not r.text.strip():
        click.secho("Error: Received empty test file. Contact your "
                    "instructor", fg="red", bold=True)
        sys.exit(1)

    if "def test_" not in r.text:
        click.secho(
            "Warning: This may not be a valid test file.",
            fg="yellow"
        )

    return r.text


def reload_module(module_name: str) -> None:
    """Reload the module. Ensures it is reloaded if previously loaded.

    :param module_name: The name of the module to reload.
    :type module_name: str
    """
    sys.modules.pop(module_name, None)
    import_module(name=module_name)


def patch_input_output(monkeypatch: Any,
                       test_inputs: list,
                       module_name: str) -> StringIO:
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
    """Format repr class type.

    :param var_type: The name of a type.
    :type var_type: str
    :return: The formatted type.
    :rtype: str
    """
    return var_type.split("'")[1::2][0] if var_type else "Your function output None, but is expected to return a value."


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
        errors.append(f"The expected and actual string lengths are "
                      f"different. Expected length: {expected_len}, but "
                      f"got length: {actual_len}.")
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
            return (f"Character '{actual[idx]}' at index {idx} does "
                    f"not match with the expect output. "
                    f"This is the first mismatched character. There "
                    f"may be others.")


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
        return ("Your program/function's output has an extra newline "
                "character \'\\n\' at the end.")


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
        return (f"There are two spaces at index {actual.index('  ')} "
                f"of your program/function's output.")


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
        return (f"The actual string exceeds the maximum allowed "
                f"length.\n Actual length is: {actual_len}\n"
                f"Limit is: {limit}")


def _construct_test_url(chapter, assignment: str) -> str:
    """Construct the URL at which the test lives."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "check_pfda", "config.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    base_url = config["tests"]["tests_repo_url"]

    # query at the end forces browser to flush cache
    return f"{base_url}/c{chapter}/test_{assignment}.py?now=0423"


def get_module_in_src() -> str:
    """Get the name of the assignment the student is working on."""
    current_path = Path.cwd()
    if not current_path.name == "src":
        src_dir = current_path / "src"
    else:
        src_dir = current_path
    py_files = list(src_dir.glob("*.py"))
    if not py_files:
        raise FileNotFoundError("No Python module found in the src/"
                                " directory.")
    if len(py_files) > 1:
        raise RuntimeError("Multiple Python modules found in src/."
                           " Expected only one.")
    return py_files[0].stem


def get_current_assignment(repo_path: Path, logger) -> dict | None:
    """
    Matches the current working directory against a YAML configuration file
    to find the corresponding chapter and assignment.

    :param repo_path: The path to the repository root.
    :type repo_path: Path
    :param logger: Logger instance for debug logging.
    :type logger: logging.Logger

    :return: A dictionary with 'chapter' and 'assignment' keys if found, None on error
    :rtype: dict | None
    """
    # Read and parse the YAML file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "check_pfda", "config.yaml")
    repo_path_str = str(repo_path)
    if "c07" in repo_path_str or "c08" in repo_path_str:
        click.secho("C07 and C08 do not have any automated tests. Refer to the README for more information.", fg="yellow")
        return None
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        logger.exception(f"YAML file not found: {config_path}")
        return None
    except yaml.YAMLError as e:
        logger.exception(f"Error parsing YAML file: {e}")
        return None
    
    """This logic is necessary because there's no way to get the name of the current assignment without some
    external source of assignment names from the student's repo's root dir. This is because assignment names
    vary in length and student names also vary in length and both may use the same delimiter. For example:
    
    pfda-c01-lab-favorite-artist-bencres-demo
    
    and
    
    pfda-c01-lab-shout-bencres-demo
    
    In this case, we can't get 'favorite-artist' or 'shout' without knowing at least one of:
    
    1. The student's GitHub username.
    2. Names of valid assignments.
    """
    # Iterate through chapters in the config
    for chapter_key, assignments in config.get('tests', {}).items():
        # Skip the tests_repo_url key
        if chapter_key == 'tests_repo_url':
            continue
        if chapter_key not in repo_path_str:
            continue
        for assignment in assignments:
            if assignment in repo_path_str.replace("-", "_"):
                result = {"chapter": str(chapter_key)[1:],
                         "assignment": str(assignment).replace("-", "_")}
                logger.debug(f"Current assignment info: {result}")
                return result
    
    # No match found
    logger.debug("Error parsing cwd and matching it against config. Contact your TA.")
    return None


def _add_src_to_sys_path(src_path: Path, logger):
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        logger.debug(f"Added {str(src_path)} to sys.path")


def _remove_src_from_sys_path(debug: bool, src_path: Path, logger):
    if str(src_path) in sys.path:
        sys.path.remove(str(src_path))
        if debug:
            logger.debug(f"Removed {str(src_path)} from sys.path")


class RepositoryNotFound(Exception):
    """Raised when the repository root cannot be located."""
    pass


def _recurse_to_repo_path(current_path: Path) -> Path:
    """Recursively search upward for a directory containing 'pfda-c'.

    :param current_path: The starting path to search upward from.
    :type current_path: Path
    :returns: The path to the directory whose name contains ``pfda-c``.
    :rtype: Path
    :raises RepositoryNotFound: If no directory named ``pfda-c`` is found up to the filesystem root.
    """
    if "pfda-c" in current_path.name:
        return current_path

    # filesystem root
    if current_path.parent == current_path:
        raise RepositoryNotFound(
            f"No 'pfda-c' repository found starting from {current_path!s}"
        )

    return _recurse_to_repo_path(current_path.parent)
