"""Command-line interface for package usage."""

import click

from .core import check_student_code


@click.command()
def cli():
    """Run student code checks."""
    check_student_code()
