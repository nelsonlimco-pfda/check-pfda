"""Collect tests and run them on supplied code."""

from click import echo
import os
import pytest
from tempfile import NamedTemporaryFile, TemporaryDirectory
from .utils.http import get_tests


def check_student_code(assignment_id: str, verbosity: int) -> None:
    """Check student code."""
    echo(f"Checking assignment {assignment_id} at verbosity {verbosity}...")
    tests = get_tests(assignment_id)

    temp_file = NamedTemporaryFile(suffix=".py", delete=False)
    try:
        temp_file.write(tests.encode("utf-8"))
        temp_file.flush()
        temp_file.close()  # Close it so that pytest (or whatever) can access it

        # Now you can safely use it, e.g.:
        # result = subprocess.run(["pytest", temp_file.name])
        echo(f"Temp test file at: {temp_file.name}")
        args = [temp_file.name]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")
        exit_code = pytest.main(args)
        echo(f"Pytest finished with exit code {exit_code}")
    finally:
        os.remove(temp_file.name)
        echo("Removed temp test file.")
