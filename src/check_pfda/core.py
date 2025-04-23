"""Collect tests and run them on supplied code."""

from click import echo
import os
import pytest
from tempfile import NamedTemporaryFile, TemporaryDirectory
from .utils.http import get_tests
from pathlib import Path


def check_student_code(verbosity: int) -> None:
    """Check student code."""
    assignment = _get_module_in_src()
    echo(f"Checking assignment {assignment} at verbosity {verbosity}...")
    tests = get_tests(assignment)

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


def _get_module_in_src() -> str:
    src_dir = Path.cwd() / "src"
    py_files = list(src_dir.glob("*.py"))
    if not py_files:
        raise FileNotFoundError("No Python module found in the src/ directory.")
    if len(py_files) > 1:
        raise RuntimeError("Multiple Python modules found in src/. Expected only one.")
    return str(py_files[0].name[:-3])  # just the filename, not the full path
