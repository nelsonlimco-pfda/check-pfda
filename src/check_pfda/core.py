"""Collect tests and run them on supplied code."""

import os
from tempfile import NamedTemporaryFile
import sys
import logging
import platform


from click import echo
import pytest
from check_pfda.utils import get_current_assignment, get_tests


logger = logging.getLogger(__name__)


def check_student_code(verbosity: int = 2, debug = False) -> None:
    """Check student code."""
    # Configure logging
    if debug:
        log_file = os.path.join(os.getcwd(), "debug.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='w'
        )
        logger.debug("Debug mode enabled")
        logger.debug(f"Debug log file: {log_file}")
        
        # Log system information
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Python executable: {sys.executable}")
        logger.debug(f"Platform: {platform.platform()}")
        logger.debug(f"System: {platform.system()} {platform.release()}")
        logger.debug(f"Machine: {platform.machine()}")
        logger.debug(f"Processor: {platform.processor()}")
        
        # Log package information
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
        
        echo(f"Debug logging enabled. Writing to: {log_file}")
    
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
    
    cwd_src = os.path.join(os.getcwd(), "src")
    if cwd_src not in sys.path:
        sys.path.insert(0, cwd_src)
        if debug:
            logger.debug(f"Added {cwd_src} to sys.path")
    
    tests = get_tests(chapter, assignment)
    if debug:
        logger.debug(f"Retrieved tests (length: {len(tests)} bytes)")

    temp_file = NamedTemporaryFile(suffix=".py", delete=False)
    try:
        if debug:
            logger.debug(f"Created temporary test file: {temp_file.name}")
        
        temp_file.write(tests.encode("utf-8"))
        temp_file.flush()
        temp_file.close()

        args = [temp_file.name]
        if verbosity > 0:
            args.append(f"-{'v' * verbosity}")
        
        if debug:
            logger.debug(f"Running pytest with args: {args}")
        
        pytest.main(args)
    finally:
        os.remove(temp_file.name)
        if debug:
            logger.debug(f"Removed temporary test file: {temp_file.name}")
    
    if cwd_src in sys.path:
        sys.path.remove(cwd_src)
        if debug:
            logger.debug(f"Removed {cwd_src} from sys.path")
