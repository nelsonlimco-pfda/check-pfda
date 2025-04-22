"""Command-line interface for package usage."""

import click

from .core import check_student_code, write_assignment_results


@click.group()
def cli():
    """Group for CLI entrypoint."""
    pass


@cli.command()
@click.argument('assignment_id')
def check(assignment_id: str) -> None:
    """Run student checks."""
    click.echo(f"Checking {assignment_id}...")
    check_student_code(assignment_id)


@cli.command()
@click.argument('assignment_id')
def admin(assignment_id: str) -> None:
    """Instructor command: writes full assignment results."""
    click.echo(f"Getting results for {assignment_id}...")
    write_assignment_results(assignment_id)
