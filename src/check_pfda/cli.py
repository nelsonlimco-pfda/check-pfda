"""Command-line interface for package usage."""

import click

from .core import check_student_code


@click.group()
def cli():
    """Group for CLI entrypoint."""
    pass


@cli.command()
@click.argument('assignment_id')
@click.option(
    '-v',
    '--verbosity',
    count=True,
    help='Verbosity of test output'
)
def check(assignment_id: str, verbosity: int) -> None:
    """Run student checks."""
    click.echo(f"Checking {assignment_id}...")
    check_student_code(assignment_id, verbosity)
