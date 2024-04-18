# System libraries.
from io import StringIO
from importlib import import_module
import os
import sys
from typing import Any


# Custom imports.
from utils.AutograderError import AutograderError


# Constants.
STRING_LEN_LIMIT = 1000
MODULE_NAME = ""
ACCEPTED_DIRS = []
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


def assert_script_exists():
    """Checks accepted subfolders for the module script."""
    curr_dir = os.getcwd()
    for subfolder in ACCEPTED_DIRS:
        filename = os.path.join(curr_dir, subfolder, f'{MODULE_NAME}.py')
        print(filename)
        if os.path.exists(filename):
            return True
    return False


# Utility functions.
def generate_temp_file(filename: str, tmpdir: str, contents: Any) -> str:
    """Generates a temporary file to test with.

    :param filename: The name of the temporary file.
    :type filename: str
    :param tmpdir: The path of the directory to store the temporary file.
    :type tmpdir: str
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
    type_expected = type(expected)
    return isinstance(expected, type_expected) and isinstance(actual, type_expected)


def handle_string(expected: str, actual: str) -> str:
    """Handles string comparison for asserting equivalency.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :raises AutograderError: If the actual string is larger than the limit.
    :return: An error message.
    :rtype: str
    """
    expected_len = len(expected)
    actual_len = len(actual)
    # Enforce a length limit in case a student accidentally makes an enormous string.
    if actual_len < STRING_LEN_LIMIT:
        detail = GENERIC + check_common_errors(actual)
        # Highlight which character differs.
        if expected_len == actual_len:
            detail += find_incorrect_char(expected, actual)
        # Else highlight the length difference.
        else:
            detail += (f"The expected and actual string lengths are different.\n"
                       f"Expected length: {expected_len}\n"
                       f"Actual length: {actual_len}")
        return detail
    else:
        # Raise for long strings.
        raise AutograderError("The actual string exceeds the maximum allowed "
                              f"length.\nLength is: {actual_len}"
                              f"\nLimit is: {STRING_LEN_LIMIT}",
                              expected=expected,
                              actual=actual)


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


def check_common_errors(actual: str) -> str:
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
    if actual[-1] == '\n':
        message += "There is a trailing newline ('\\n') at the end of the actual string. "
    return message


def reload_module():
    """Reloads the module. Ensures it is reloaded if previously loaded."""
    sys.modules.pop(MODULE_NAME, None)
    import_module(name=MODULE_NAME)


def patch_input_output(monkeypatch, test_inputs):
    """Patches input() and standard out. Returns the patched standard out."""
    # patches the standard output to catch the output of print()
    patch_stdout = StringIO()
    # Returns a new mock object which undoes any patching done inside
    # the with block on exit to avoid breaking pytest itself.
    with monkeypatch.context() as m:
        # patches the input()
        m.setattr('builtins.input', lambda _: test_inputs.pop(0))
        m.setattr('sys.stdout', patch_stdout)
        reload_module()
    return patch_stdout
