"""Collect tests and run them on supplied code."""

import os
from pathlib import Path
import sys
import logging
import platform


from click import echo
import pytest
from check_pfda.utils import get_current_assignment, get_tests


logger = logging.getLogger(__name__)


def _init_logger(log_file: str):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w'
    )


def _log_platform_info():
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Python executable: {sys.executable}")
    logger.debug(f"Platform: {platform.platform()}")
    logger.debug(f"System: {platform.system()} {platform.release()}")
    logger.debug(f"Machine: {platform.machine()}")
    logger.debug(f"Processor: {platform.processor()}")


def _log_package_info(log_file: str):
    logger.debug(f"Installed packages:")
    try:
        import pkg_resources
        installed_packages = [(d.project_name, d.version) for d in pkg_resources.working_set]
        installed_packages.sort()
        for package_name, version in installed_packages:
            logger.debug(f"  {package_name}=={version}")
    except Exception as e:
        logger.debug(f"Unable to retrieve package information: {e}")

    # Log current working directory and sys.path
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"sys.path: {sys.path}")


def check_student_code(verbosity: int = 2, debug = False) -> None:
    """Check student code."""
    # Configure logging
    root_path = Path.cwd()
    if root_path.name == "src":
        root_path = root_path.parent

    src_path = root_path / "src"
    if debug:
        log_file = os.path.join(root_path, "debug.log")
        _init_logger(log_file)
        logger.debug("Debug mode enabled")
        logger.debug(f"Debug log file: {log_file}")
        _log_platform_info()
        _log_package_info(log_file)
        echo(f"Debug logging enabled. Writing to {log_file}.")
        
    try:
        current = get_current_assignment()
        if debug:
            logger.debug(f"Current assignment info: {current}")
    except TypeError:
        echo("Unable to match chapter and assignment against cwd. Contact your TA.")
        if debug:
            logger.exception("Failed to get current assignment")
        return
    chapter = current["chapter"]
    assignment = current["assignment"]
    echo(f"Checking assignment {assignment} at verbosity {verbosity}...")
    
    if debug:
        logger.debug(f"Chapter: {chapter}, Assignment: {assignment}")
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        if debug:
            logger.debug(f"Added {str(src_path)} to sys.path")
    
    tests = get_tests(chapter, assignment)
    if debug:
        logger.debug(f"Retrieved tests (length: {len(tests)} bytes)")

    tests_dir = root_path / ".tests"
    tests_dir.mkdir(exist_ok=True)
    
    if debug:
        logger.debug(f"Created/verified .tests directory: {tests_dir}")
    
    # Write test file to .tests directory
    test_file_path = tests_dir / f"test_{assignment}.py"
    
    try:
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(tests)
        
        if debug:
            logger.debug(f"Wrote test file to: {test_file_path}")

        args = [str(test_file_path)]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")
        
        if debug:
            logger.debug(f"Running pytest with args: {args}")
        
        pytest.main(args)
    except Exception as e:
        echo(f"Error writing or running test file: {e}")
        if debug:
            logger.exception("Failed to write or run test file")
    
    if str(src_path) in sys.path:
        sys.path.remove(str(src_path))
        if debug:
            logger.debug(f"Removed {str(src_path)} from sys.path")
