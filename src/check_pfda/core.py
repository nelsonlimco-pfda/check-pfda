"""Collect tests and run them on supplied code."""

import os
from tempfile import NamedTemporaryFile


from check_pfda.utils import get_module_in_src, get_tests

from click import echo

import pytest


def check_student_code(verbosity: int) -> None:
    """Check student code."""
    assignment = get_module_in_src()
    echo(f"Checking assignment {assignment} at verbosity {verbosity}...")
    tests = get_tests(assignment)

    temp_file = NamedTemporaryFile(suffix=".py", delete=False)
    try:
        temp_file.write(tests.encode("utf-8"))
        temp_file.flush()
        temp_file.close()

        echo(f"Temp test file at: {temp_file.name}")
        args = [temp_file.name]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")
        exit_code = pytest.main(args)
        echo(f"Pytest finished with exit code {exit_code}")
    finally:
        os.remove(temp_file.name)
        echo("Removed temp test file.")
