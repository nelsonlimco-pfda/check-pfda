"""Command-line interface for package usage."""

import click

from .core import check_student_code


@click.group()
def cli():
    """Group for CLI entrypoint."""
    pass


@cli.command()
@click.option(
    '-v',
    '--verbosity',
    count=True,
    help='Verbosity of test output'
)
def check(verbosity: int) -> None:
    """Run student checks."""
    check_student_code(verbosity)
