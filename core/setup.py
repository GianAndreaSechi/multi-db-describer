from setuptools import setup, find_packages

setup(
    name='core',
    version='0.1.0',
    packages=find_packages(),
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
    ],
)
