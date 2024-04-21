# System libraries.
from io import StringIO
from importlib import import_module
import os
import py.path
import sys
from typing import Any


# PyPi libraries.
import pytest


# Custom imports.
from utils.AutograderError import AutograderError


# Constants.
STRING_LEN_LIMIT = 1000
GENERIC = "The test failed. "


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
    if expected != actual:
        # Raise for different expected and actual types.
        # TODO: gut feeling there is a more sensible way to do this.
        if not is_same_type(expected, actual):
            raise AutograderError(f"{GENERIC} Expected and actual types differ.\n"
                                  f"Expected type: {type(expected)}\n"
                                  f"Actual type: {type(actual)}")
        # Final error message.
        raise AutograderError(f"""{GENERIC if not is_str else 
                              handle_string(expected, actual)}""",
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


def is_same_type(expected: Any, actual: Any) -> bool:
    """Evaluates if the two arguments are the same type.

    :param expected: The expected object.
    :type expected: Any
    :param actual: The actual object.
    :type actual: Any
    :return: If the two objects are the same type.
    :rtype: bool
    """
    return isinstance(actual, type(expected))


def handle_string(expected: str, actual: str) -> str:
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
    if actual_len < STRING_LEN_LIMIT:
        common_errors = check_common_errors(actual)
        detailed_error_msg = GENERIC + common_errors if common_errors else GENERIC
        # Highlight which character differs.
        if expected_len == actual_len:
            detailed_error_msg += find_incorrect_char(expected, actual)
        # Else highlight the length difference.
        else:
            detailed_error_msg += (f"The expected and actual string lengths are "
                                   f"different.\nExpected length: {expected_len}\n"
                                   f"Actual length: {actual_len}")
        return detailed_error_msg
    return (f"The actual string exceeds the maximum allowed length.\n"
            f"Actual length is: {actual_len}\nLimit is: {STRING_LEN_LIMIT}")


def find_incorrect_char(expected: str, actual: str) -> str:
    """Finds the index of an actual character that does not match
    the expected character.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :return: A string containing the incorrect character and its index.
    :rtype: str
    """
    for idx, char in enumerate(expected):
        if char != actual[idx]:
            return (f"Character '{actual[idx]}' at index {idx} of "
                    f"the actual does not match the expected.")


def check_common_errors(actual: str) -> str | None:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :return: A string to concatenate to the error if there are common errors, otherwise
    None.
    :rtype: str | None
    """
    message = ""
    # Check for double spaces.
    if '  ' in actual:
        message += f"There are two spaces at index: {actual.index('  ')}. "
    # Check for trailing newlines.
    if actual.endswith('\n'):
        message += "There is a trailing newline ('\\n') at the end of the actual string. "
    return message or None


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
