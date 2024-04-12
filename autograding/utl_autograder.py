# System imports.
import io
import importlib
import os
import sys


# Custom imports.
from utl_AutograderError import AutograderError


# Constants.
STRING_LEN_THRESHOLD = 1000
MODULE_NAME = ""
ACCEPTED_DIRS = []
GENERIC = "The test failed. "


# Global lambdas.
current_func_name = lambda n=0: sys._getframe(n + 1).f_code.co_name


def assert_equal(expected, actual):
    """Checks that two variables are equal. If not, raises an informative error.

    :param expected: The expected value.
    :param actual: The actual value.
    :raises AutograderError: Error message containing detailed information about
    each value.
    :return: None
    """
    # Raise for different expected and actual types.
    if type(expected) != type(actual):
        raise AutograderError(f"{GENERIC} Expected and actual types differ.\n"
                              f"Expected type: {type(expected)}\n"
                              f"Actual type: {type(actual)}")
    is_str = isinstance(expected, str)
    if expected != actual:
        if is_str:
            detail = handle_string(expected, actual)
        # Final error message.
        raise AutograderError(f"{GENERIC if not is_str else detail}",
                              expected=expected,
                              actual=actual,
                              context=current_func_name(1))


def handle_string(expected:str, actual:str) -> str:
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
    if actual_len < STRING_LEN_THRESHOLD:
        common_errors = check_for_common_errors(actual)
        detail = ""
        detail += GENERIC
        detail += common_errors if common_errors else ""
        # Highlight which character differs.
        if expected_len == actual_len:
            detail += find_incorrect_char(expected, actual)
        # Else highlight the length difference.
        else:
            detail += (f"The expected and actual string lengths are different.\n"
                       f"Expected length: {expected_len}\n"
                       f"Actual length: {actual_len}")
        return detail
    # Raise for long strings.
    else:
        raise AutograderError("The actual string exceeds the maximum allowed "
                              f"length.\nLength is: {actual_len}"
                              f"\nLimit is: {STRING_LEN_THRESHOLD}",
                              expected=expected,
                              actual=actual,
                              context=current_func_name(1))


def find_incorrect_char(expected:str, actual:str) -> str:
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
            return (f"Character '{char}' at index {idx} of "
                    f"the expected does not match the actual.")


def check_for_common_errors(actual:str) -> str | None:
    """Check the actual string for common errors.

    :param actual: The actual string.
    :return: A string to concatenate to the error if there are common errors, otherwise None.
    :rtype: str | None
    """
    message = ""
    # Check for double spaces.
    for idx, char in enumerate(actual):
        if char == ' ' and actual[idx + 1] == ' ':
            message += f"There are two spaces at index: {idx}. "
            break
    # Check for trailing newlines.
    if actual[-1] == '\n':
        message += "There is a trailing newline ('\\n') at the end of the actual string. "
    return message if not message == "" else None


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