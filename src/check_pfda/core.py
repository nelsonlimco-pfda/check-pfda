"""Collect tests and run them on supplied code."""

from click import echo


def check_student_code(assignment_id: str) -> None:
    """Check student code."""
    echo(f"Checking assignment {assignment_id}...")


"""Collect results and format them."""


def write_assignment_results(assignment_id: str) -> None:
    """Write assignment results to CSV."""
    echo(f"Writing results for {assignment_id}...")
