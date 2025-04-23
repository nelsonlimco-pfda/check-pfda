"""Functions to supplement HTTP operations."""

from click import echo
import os
import requests
import yaml


def get_tests(assignment_id: str) -> str:
    """Get tests for a given assignment"""
    # Get the path to the current file (http.py), then go up one directory
    tests_repo_url = _construct_test_url(assignment_id)
    echo(f"Tests repo url: {tests_repo_url}")


def _construct_test_url(assignment_id):
    """Construct the url to get the test from"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, ".config", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    # echo(f"{config["tests"]}")
    # Access the URL or id_map from the config
    tests_repo_url = (f"{config['tests']['tests_repo_url']}"
                      f"{config['tests']['test_id_map'][assignment_id]}.py")
    return tests_repo_url
