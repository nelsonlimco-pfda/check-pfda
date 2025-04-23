"""Collect tests and run them on supplied code."""

from click import echo
from .utils.http import get_tests


def check_student_code(assignment_id: str, verbosity: int) -> None:
    """Check student code."""
    echo(f"Checking assignment {assignment_id} at verbosity {verbosity}...")
    get_tests(assignment_id)
