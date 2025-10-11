"""Command-line interface for package usage."""

import click

from .core import check_student_code


@click.command()
@click.option(
    '-v', '--verbosity',
    default=2,
    type=int,
    help='Set verbosity level (0-3). Default is 2.'
)
@click.option(
    '-d', '--debug',
    is_flag=True,
    default=False,
    help='Enable debug mode.'
)
def cli(verbosity, debug):
    """Run student code checks."""
    check_student_code(verbosity=verbosity, debug=debug)
