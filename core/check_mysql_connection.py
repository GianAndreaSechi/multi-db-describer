import sys
import traceback
from core.db_connector.connectors.mysql import MySQLConnector
from loguru import logger # New import

MYSQL_TEST_CONFIG = {
    "host": "host.docker.internal",
    "user": "root",
    "password": "",
    "port": 3306,
}

try:
    logger.info("Attempting MySQL connection check...")
    temp_conn = MySQLConnector(connection_params=MYSQL_TEST_CONFIG)
    logger.info("MySQL connection successful!")
except Exception as e:
    logger.error(f"MySQL connection failed: {e}")
    logger.exception("Connection Error Traceback:")
    sys.exit(1) # Exit with error code if connection fails
