"""Functions to supplement HTTP operations."""

from click import echo
import os
import requests
import yaml


def get_tests(assignment_id: str) -> str:
    """Get tests for a given assignment"""
    tests_repo_url = _construct_test_url(assignment_id)
    try:
        r = requests.get(tests_repo_url, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        click.secho(f"Error fetching test file for assignment '"
                    f"{assignment_id}': {e}", fg="red", bold=True)
        sys.exit(1)

    if not r.text.strip():
        click.secho("Error: Received empty test file. Contact your "
                    "instructor", fg="red", bold=True)
        sys.exit(1)

    if "def test_" not in r.text:
        click.secho("Warning: This may not be a valid test file.", fg="yellow")

    return r.text


def _construct_test_url(assignment_id):
    """Construct the url to get the test from"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, ".config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    # echo(f"{config["tests"]}")
    # Access the URL or id_map from the config
    tests_repo_url = (f"{config['tests']['tests_repo_url']}"
                      f"{config['tests']['test_id_map'][assignment_id]}.py?"
                      f"now=0423")
    echo(f"Tests repo url: {tests_repo_url}")
    return tests_repo_url
