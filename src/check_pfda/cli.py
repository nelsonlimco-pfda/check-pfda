"""Command-line interface for package usage."""

import click

from .core import check_student_code


@click.command()
def cli():
    """Run student code checks."""
    check_student_code()


# @cli.command()
# @click.option(
#     '-v',
#     '--verbosity',
#     count=True,
#     help='Verbosity of test output'
# )
# @click.option(
#     '-d',
#     '--debug',
#     is_flag=True,
#     help='Swap to offline tests'
# )
# def check(verbosity: int, debug: bool) -> None:
#     """Run student checks."""
#     check_student_code(verbosity, debug)
