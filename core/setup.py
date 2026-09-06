from pathlib import Path

from setuptools import find_packages, setup


# ``setup.py`` lives inside the ``core`` package directory.  Prefix the
# discovered subpackages so an installed distribution exposes the same public
# imports used by the services: ``core.db_connector``.
packages = [
    "core",
    *[f"core.{package}" for package in find_packages(where=str(Path(__file__).parent))],
]

setup(
    name='irides-core',
    version='0.1.0',
    packages=packages,
    package_dir={"core": "."},
    install_requires=[
        'pydantic',
        'redis',
        'mysql-connector-python',
        'pytest',
        'duckdb',
        'loguru',
        'boto3',
        'pymongo',
        'psycopg2-binary',
        'trino',
        'python-dotenv',
        'litellm',
        'PyYAML',
    ],
)
