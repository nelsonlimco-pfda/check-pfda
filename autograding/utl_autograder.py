# System imports.
import io
import inspect
import importlib
import os
import sys
from typing import Any


# Custom imports.
from utl_AutograderError import AutograderError


# Constants.
STRING_LEN_LIMIT = 1000
MODULE_NAME = ""
ACCEPTED_DIRS = []
GENERIC = "The test failed. "


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
        if not check_same_type(expected, actual):
            raise AutograderError(f"{GENERIC} Expected and actual types differ.\n"
                                  f"Expected type: {type(expected)}\n"
                                  f"Actual type: {type(actual)}")
        if is_str:
            detail = handle_string(expected, actual)
        # Final error message.
        raise AutograderError(f"{GENERIC if not is_str else detail}",
                              expected=expected,
                              actual=actual,
                              context=construct_traceback(3))


def check_same_type(expected, actual):
    type_expected = type(expected)
    return isinstance(expected, type_expected) and isinstance(actual, type_expected)


def handle_string(expected: str, actual: str) -> str:
    """Handles string comparison for asserting equivalency.

    :param expected: The expected string.
    :type expected: str
    :param actual: The actual string.
    :type actual: str
    :raises AutograderError: If strings lengths are different or the actual  
    string is larger than the threshold.
    :return: An error message.
    :rtype: str
    """
    expected_len = len(expected)
    actual_len = len(actual)
    # Enforce a length limit in case a student accidentally makes an enormous string.
    if actual_len < STRING_LEN_LIMIT:
        common_errors = check_common_errors(actual)
        detail = GENERIC + common_errors if common_errors else GENERIC
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
                              actual=actual,
                              context=construct_traceback(3))


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
    if actual[-1] == '\n':
        message += "There is a trailing newline ('\\n') at the end of the actual string. "
    return message if not message == "" else None


def construct_traceback(n: int = 0) -> str:
    """Constructs a traceback message containing the function name, file path, and line
    number.

    :param n: How many code frames back to construct the traceback from.
    :type n: int
    :return: A traceback string.
    :rtype: str
    """
    frames = [inspect.currentframe()]
    if n > 0:
        for i in range(n):
            frames.append(frames[i].f_back)
    return (f"<{frames[n - 1].f_code.co_name}> in file '"
            f"{frames[n - 1].f_code.co_filename}'"
            f" at line: {frames[n].f_lineno}")


def assert_script_exists():
    """Checks accepted subfolders for the module script."""
    curr_dir = os.getcwd()
    for subfolder in ACCEPTED_DIRS:
        filename = os.path.join(curr_dir, subfolder, f'{MODULE_NAME}.py')
        print(filename)
        if os.path.exists(filename):
            return True
    return False


def reload_module():
    """Reloads the module. Ensures it is reloaded if previously loaded."""
    sys.modules.pop(MODULE_NAME, None)
    importlib.import_module(name=MODULE_NAME)


def patch_input_output(monkeypatch, test_inputs):
    """Patches input() and standard out. Returns the patched standard out."""
    # patches the standard output to catch the output of print()
    patch_stdout = io.StringIO()
    # Returns a new mock object which undoes any patching done inside
    # the with block on exit to avoid breaking pytest itself.
    with monkeypatch.context() as m:
        # patches the input()
        m.setattr('builtins.input', lambda _: test_inputs.pop(0))
        m.setattr('sys.stdout', patch_stdout)
        reload_module()
    return patch_stdout
