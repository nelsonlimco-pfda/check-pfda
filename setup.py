"""Setup file, containing package metadata."""
from setuptools import find_packages, setup

setup(
    name='check-pfda',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'pytest',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'check = pfda_tester.src.cli:run_test',
        ]
    }
)
