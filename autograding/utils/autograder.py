# System libraries.
from io import StringIO
from importlib import import_module
import os
import py.path
import sys
from typing import Any


# PyPi libraries.
import pytest


class AutograderError(Exception):
    def __init__(self, message, expected=None, actual=None, extra_info=None):
        super().__init__(message)
        self.expected = expected
        self.actual = actual
        self.context = extra_info

    def __str__(self):
        error_msg = super().__str__()
        if self.actual or self.expected:
            error_msg += f"\nExpected: {repr(self.expected)}\nActual: {repr(self.actual)}"
        if self.context:
            error_msg += f"\nContext: {self.context}"
        return error_msg


# Constants.
STRING_LEN_LIMIT = 1000


# Assertions.
def assert_equal(expected: Any, actual: Any) -> None:
    """Checks that two variables are equal. If not, raises an informative error.

    :param expected: The expected value.
    :param actual: The actual value.
    :raises AutograderError: Error message containing detailed information about
    each value.
    :return: None
    """
    is_str = isinstance(expected, str)
    # Raise for different expected and actual types.
    if is_different_type(expected, actual):
        raise AutograderError(f"Expected and actual types differ. "
                              f"Expected value: {expected} of type: "
                              f"{format_type(str(type(expected)))}, but got value: "
                              f"{actual} of type: {format_type(str(type(actual)))}")
    if expected != actual:
        raise AutograderError(f"""
        {build_string_error(expected, actual) if is_str else "Error."}""",
                              expected=expected,
                              actual=actual)


def assert_script_exists(module_name: str, accepted_dirs: list) -> None:
    """Checks accepted subfolders for the module script.

    :param module_name: The name of the module to check.
    :type module_name: str
    :param accepted_dirs: The accepted subfolders for the script.
    :type accepted_dirs: list
    :raises AutograderError: If the script does not exist.
    :return: None"""
    curr_dir = os.getcwd()
    for subfolder in accepted_dirs:
        filename = os.path.join(curr_dir, subfolder, f'{module_name}.py')
        print(filename)
        if os.path.exists(filename):
            return None
    raise AutograderError("The script does not exist. "
                          "The most likely cause is that the current working directory "
                          "is not `src`. Make sure that you ran `cd src` in the "
                          "terminal before you executed the script.\n")


# Utility functions.
def format_type(var_type: str) -> str:
    """Formats repr class type.
    :param var_type: The type of a variable.
    :return: The formatted type.
    """
    return var_type.split("'")[1::2][0]


def generate_temp_file(filename: str, tmpdir: py.path.local, contents: Any) -> str:
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
    with open(filepath, 'w') as f:
        f.write(contents)
    return filepath


def is_different_type(expected: Any, actual: Any) -> bool:
    """Evaluates if the two arguments are the same type.

    :param expected: The expected object.
    :type expected: Any
    :param actual: The actual object.
    :type actual: Any
    :return: If the two objects are the same type.
    :rtype: bool
    """
    return not isinstance(actual, type(expected))


def build_string_error(expected: str, actual: str) -> str:
    """Handles string comparison for asserting equivalency.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: An error message.
    :rtype: str
    """
    expected_len = len(expected)
    actual_len = len(actual)
    # Enforce a length limit in case a student accidentally makes an enormous string.
    if actual_len > STRING_LEN_LIMIT:
        return (f"The actual string exceeds the maximum allowed length.\n"
            f"Actual length is: {actual_len}\nLimit is: {STRING_LEN_LIMIT}")
    error_msg = ""
    if check_double_spaces(actual):
        error_msg += find_double_spaces(actual)
    if check_trailing_newline(actual):
        error_msg += find_trailing_newline(actual)
    # Highlight which character differs.
    if expected_len == actual_len:
        error_msg += find_incorrect_char(expected, actual)
    # Else highlight the length difference.
    else:
        error_msg += (f"The expected and actual string lengths are "
                               f"different. Expected length: {expected_len}, but "
                               f"got length: {actual_len}. Expected {repr(expected)} "
                               f"but got: {repr(actual)}")
    return error_msg


def find_incorrect_char(expected: str, actual: str) -> str:
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
            return (f"Character '{actual[idx]}' at index {idx} of "
                    f"the actual is the first that does not match. Expected"
                    f" {repr(expected)} but got {repr(actual)}")


def check_trailing_newline(actual: str) -> str | None:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :return: A string to concatenate to the error if there are common errors, otherwise
    None.
    :rtype: str | None
    """
    if actual.endswith('\n'):
        return True
    return False


def find_trailing_newline(actual: str) -> str:
    """Returns a string with the location of the newline.

    :param actual: The actual string.
    :return: An error string with the location of the newline.
    """
    return "There is a trailing newline ('\\n') at the end of the actual string. "


def check_double_spaces(actual: str) -> bool:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :return: A string to concatenate to the error if there are common errors, otherwise
    None.
    :rtype: str | None
    """
    message = ""
    # Check for double spaces.
    if '  ' in actual:
        return True
    return False

def find_double_spaces(actual: str) -> str:
    """Finds the location of the double spaces in the actual string and
    builds an error string.

    :param actual: The actual string.
    :return: An error message containing the location of the double spaces in the actual.
    """
    return f"There are two spaces at index: {actual.index('  ')}. "

def reload_module(module_name: str) -> None:
    """Reloads the module. Ensures it is reloaded if previously loaded.

    :param module_name: The name of the module to reload.
    :type module_name: str
    :return: None"""
    sys.modules.pop(module_name, None)
    import_module(name=module_name)


def patch_input_output(monkeypatch: Any, test_inputs: list, module_name: str) -> StringIO:
    """Patches input() and standard out.

    :param monkeypatch: Pytest's monkeypatch fixture.
    :type monkeypatch: Monkeypatch #TODO: doesn't look like it's possible to type hint?
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
        m.setattr('builtins.input', lambda _: test_inputs.pop(0))
        m.setattr('sys.stdout', patch_stdout)
        reload_module(module_name)
    return patch_stdout
