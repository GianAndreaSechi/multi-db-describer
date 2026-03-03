import pytest
from core.db_connector.connectors.mysql import MySQLConnector
from core.db_connector.models import Instance, Schema, Table, Column

# --- Configuration for MySQL Test (ADJUST THESE VALUES) ---
# For a real test, you would need a running MySQL instance.
# Consider using Docker for a temporary test database.
MYSQL_TEST_CONFIG = {
    "host": "localhost",
    "user": "test_user",
    "password": "test_password",
    "port": 3306,
    # "database": "test_db" # Optional, for specific database operations
}
# ----------------------------------------------------------

# Skip MySQL tests if configuration is not set or if connection fails
try:
    # Attempt a connection to verify config (without selecting a specific DB)
    # This is just a preliminary check, actual tests will use the fixture
    temp_conn = MySQLConnector(connection_params=MYSQL_TEST_CONFIG)
    MYSQL_IS_AVAILABLE = True
except (ValueError, ConnectionError) as e:
    print(f"MySQL test skipped: {e}")
    MYSQL_IS_AVAILABLE = False

mysql_skip_reason = "MySQL test configuration is invalid or connection failed."
pytestmark = pytest.mark.skipif(not MYSQL_IS_AVAILABLE, reason=mysql_skip_reason)

@pytest.fixture(scope="module")
def mysql_connector():
    """Fixture to provide an initialized MySQLConnector."""
    # Ensure a test database exists and has some data for testing
    # This part would typically be handled by a setup script or Docker compose
    # For this example, we assume 'test_db' exists and has 'test_table'
    
    # Example setup for a test database and table:
    # CREATE DATABASE IF NOT EXISTS test_db;
    # USE test_db;
    # CREATE TABLE IF NOT EXISTS test_table (
    #     id INT AUTO_INCREMENT PRIMARY KEY,
    #     name VARCHAR(255) NOT NULL,
    #     value INT
    # );
    # INSERT INTO test_table (name, value) VALUES ('item1', 10), ('item2', 20);

    connector = MySQLConnector(connection_params=MYSQL_TEST_CONFIG)
    yield connector
    # Teardown (optional): clean up test data or drop test database
    # For simplicity, not implemented here.

def test_mysql_get_type():
    assert MySQLConnector.get_type() == "mysql"

def test_mysql_list_instances(mysql_connector):
    instances = mysql_connector.list_instances()
    assert len(instances) == 1
    assert instances[0].name == MYSQL_TEST_CONFIG["host"]
    assert instances[0].version is not None

def test_mysql_list_schemas(mysql_connector):
    schemas = mysql_connector.list_schemas(instance_name=MYSQL_TEST_CONFIG["host"])
    # Assert that 'test_db' (or your chosen test database) is in the list
    assert any(s.name == "test_db" for s in schemas)

def test_mysql_list_tables(mysql_connector):
    tables = mysql_connector.list_tables(
        instance_name=MYSQL_TEST_CONFIG["host"], schema_name="test_db"
    )
    assert any(t.name == "test_table" for t in tables)
    assert all(t.schema_name == "test_db" for t in tables)

def test_mysql_describe_table(mysql_connector):
    columns = mysql_connector.describe_table(
        instance_name=MYSQL_TEST_CONFIG["host"], schema_name="test_db", table_name="test_table"
    )
    assert len(columns) == 3 # id, name, value
    
    col_names = {c.name for c in columns}
    assert "id" in col_names
    assert "name" in col_names
    assert "value" in col_names

    id_col = next(c for c in columns if c.name == "id")
    assert id_col.data_type == "int" # MySQL type might be 'int(11)' or similar, adjust if needed
    assert not id_col.is_nullable

    name_col = next(c for c in columns if c.name == "name")
    assert name_col.data_type == "varchar(255)" # Adjust type if needed
    assert not name_col.is_nullable

    value_col = next(c for c in columns if c.name == "value")
    assert value_col.data_type == "int" # Adjust type if needed
    assert value_col.is_nullable # Assuming default INT is nullable
