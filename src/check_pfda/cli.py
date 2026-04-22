"""Command-line interface for package usage."""
import logging
from pathlib import Path

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
    '--dir',
    'tests_dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help=(
        'Use test files from this local directory (layout: <dir>/cXX/test_<assignment>.py) '
        'instead of downloading from the configured remote tests repo.'
    ),
)
@click.option(
    '--debug',
    is_flag=True,
    default=False,
    help='Enable debug mode.',
)
def cli(verbosity, tests_dir, debug):
    """Run student code checks."""
    check_student_code(
        verbosity=verbosity,
        logger_level=logging.DEBUG if debug else logging.INFO,
        tests_dir=tests_dir,
    )
