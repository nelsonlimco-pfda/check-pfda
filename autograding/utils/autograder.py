# System libraries.
from io import StringIO
from importlib import import_module
import os
import py.path
import sys
from typing import Any

# Constants.
STRING_LEN_LIMIT = 1000

"""
Public functions. These are intended for direct implementation in unit tests.
"""


def assert_script_exists(module_name: str, accepted_dirs: list) -> None:
    """Checks accepted subfolders for the module script.

    :param module_name: The name of the module to check.
    :type module_name: str
    :param accepted_dirs: The accepted subfolders for the script.
    :type accepted_dirs: list
    :return: None"""
    curr_dir = os.getcwd()
    for subfolder in accepted_dirs:
        filename = os.path.join(curr_dir, subfolder, f"{module_name}.py")
        print(filename)
        if os.path.exists(filename):
            return None
    assert False, (
        f"The script '{module_name}.py' does not exist in the accepted "
        f"directories: {accepted_dirs}."
    )


def build_user_friendly_err(actual: Any, expected: Any) -> str:
    """Builds a user-friendly error message to accompany a pytest
    AssertionError.

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
            f"{_format_type(type(actual))}."
        )
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
        f"\n---------------------"
    )
    return error_msg


def generate_temp_file(filename: str,
                       tmpdir: py.path.local,
                       contents: Any) -> str:
    """Generates a temporary file to test with.

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


def reload_module(module_name: str) -> None:
    """Reloads the module. Ensures it is reloaded if previously loaded.

    :param module_name: The name of the module to reload.
    :type module_name: str
    :return: None"""
    sys.modules.pop(module_name, None)
    import_module(name=module_name)


def patch_input_output(monkeypatch: Any,
                       test_inputs: list,
                       module_name: str) -> StringIO:
    """Patches input() and standard out.

    :param monkeypatch: Pytest's monkeypatch fixture.
    :type monkeypatch: Monkeypatch
    :param test_inputs: The inputs to test known outputs against.
    :type test_inputs: list
    :param module_name: The name of the module to test.
    :type module_name: str
    :return: The patched standard out.
    :rtype: StringIO"""
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
    """Formats repr class type.
    :param var_type: The name of a type.
    :return: The formatted type.
    """
    return var_type.split("'")[1::2][0]


def _is_different_type(expected: Any, actual: Any) -> bool:
    """Evaluates if the two arguments are the same type.

    :param expected: The expected object.
    :type expected: Any
    :param actual: The actual object.
    :type actual: Any
    :return: If the two objects are the same type.
    :rtype: bool
    """
    return not isinstance(actual, type(expected))


def _find_string_comparison_errors(expected: str, actual: str) -> list:
    """Handles string comparison for asserting equivalency.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: An error message.
    :rtype: str
    """
    errors = []
    expected_len = len(expected)
    actual_len = len(actual)
    # Enforce a length limit in case a student
    # accidentally makes an enormous string.
    if actual_len > STRING_LEN_LIMIT:
        errors.append(f"The actual string exceeds the maximum allowed "
                      f"length.\n Actual length is: {actual_len}\n"
                      f"Limit is: {STRING_LEN_LIMIT}")
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


def _find_incorrect_char(expected: str, actual: str) -> str | None:
    """Finds the index of the first actual character that does not match
    the expected character.

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
                    f"not match with the expect output."
                    f"This is the first mismatched character. There"
                    f"may be others.")


def _check_trailing_newline(expected: str, actual: str) -> str | None:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :type actual: str
    :param expected: The expected string.
    :type expected: str
    :return: A string to concatenate to the error if there are
    common errors, otherwise None.
    :rtype: str | None
    """
    if actual.endswith("\n") and not expected.endswith("\n"):
        return ("Your program/function's output has an extra newline "
                "character ('\\n') at the end.")


def _check_double_spaces(expected: str, actual: str) -> str | None:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :return: A string to concatenate to the error if there are
    common errors, otherwise None.
    :rtype: str | None
    """
    # Check for double spaces.
    if "  " in actual and "  " not in expected:
        return (f"There are two spaces at index {actual.index('  ')} "
                f"of your program/function's output.")
