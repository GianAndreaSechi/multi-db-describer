import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from core.db_connector.models import Instance, Schema, Table
from core.db_connector.models.table_details import TableDescription
from core.db_connector.models.scan_job import ScanJob, ScanScope, ScanStatus
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Shared mocks applied before the app module is imported
# ---------------------------------------------------------------------------

_FAKE_INSTANCE = Instance(name="db.host.local")
_FAKE_SCHEMA = Schema(name="mydb")
_FAKE_TABLE = Table(name="users", schema_name="mydb")
_FAKE_TABLE_DESC = TableDescription(
    instance_name="db.host.local",
    schema_name="mydb",
    table_name="users",
    columns=[],
)
_FAKE_JOB = ScanJob(
    job_id="test-job-id",
    status=ScanStatus.PENDING,
    scope=ScanScope(config_name="cfg"),
    created_at=datetime.now(timezone.utc),
)


@pytest.fixture(scope="module")
def client():
    mock_config_service = MagicMock()
    mock_config_service.get_available_configurations.return_value = ["mysql_dev"]
    mock_config_service.test_connection.return_value = {"message": "Successfully connected to all hosts in mysql_dev."}

    mock_instance_service = MagicMock()
    mock_instance_service.list_instances.return_value = [_FAKE_INSTANCE]

    mock_schema_service = MagicMock()
    mock_schema_service.list_schemas.return_value = [_FAKE_SCHEMA]

    mock_table_service = MagicMock()
    mock_table_service.list_tables.return_value = [_FAKE_TABLE]

    mock_describe_service = MagicMock()
    mock_describe_service.describe_table.return_value = [_FAKE_TABLE_DESC]

    mock_scan_service = MagicMock()
    mock_scan_service.enqueue_scan.return_value = _FAKE_JOB
    mock_scan_service.get_job.return_value = _FAKE_JOB
    mock_scan_service.get_job_results.return_value = []
    mock_scan_service.list_jobs.return_value = [_FAKE_JOB]

    with (
        patch("api.src.main.CacheManager"),
        patch("api.src.main.ConnectorManager"),
        patch("api.src.main.ConfigService", return_value=mock_config_service),
        patch("api.src.main.InstanceService", return_value=mock_instance_service),
        patch("api.src.main.SchemaService", return_value=mock_schema_service),
        patch("api.src.main.TableService", return_value=mock_table_service),
        patch("api.src.main.DescribeTableService", return_value=mock_describe_service),
        patch("api.src.main.JobStore"),
        patch("api.src.main.ScanService", return_value=mock_scan_service),
    ):
        from api.src.main import app
        yield TestClient(app)


class TestHealthEndpoints:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_ping_returns_pong(self, client):
        resp = client.get("/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Pong!"
        assert data["data"]["status"] == "success"


class TestConfigurationsEndpoint:
    def test_returns_config_names(self, client):
        resp = client.get("/configurations")
        assert resp.status_code == 200
        assert "mysql_dev" in resp.json()["data"]


class TestConnectEndpoint:
    def test_successful_connection(self, client):
        resp = client.post("/connect", json={"config_name": "mysql_dev"})
        assert resp.status_code == 200
        assert "Successfully connected" in resp.json()["data"]["message"]

    def test_unknown_config_returns_400(self, client):
        with patch("api.src.main.config_service") as mock_cs:
            mock_cs.test_connection.side_effect = ValueError("not found")
            resp = client.post("/connect", json={"config_name": "unknown"})
        assert resp.status_code == 400


class TestInstancesEndpoint:
    def test_returns_instances(self, client):
        resp = client.post("/instances", json={"config_name": "mysql_dev"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "db.host.local"

    def test_no_cache_header_accepted(self, client):
        resp = client.post(
            "/instances",
            json={"config_name": "mysql_dev"},
            headers={"no-cache": "true"},
        )
        assert resp.status_code == 200


class TestSchemasEndpoint:
    def test_returns_schemas(self, client):
        resp = client.post(
            "/schemas",
            json={"config_name": "mysql_dev", "instance_name": "db.host.local"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data[0]["name"] == "mydb"


class TestTablesEndpoint:
    def test_returns_tables(self, client):
        resp = client.post(
            "/tables",
            json={
                "config_name": "mysql_dev",
                "instance_name": "db.host.local",
                "schema_name": "mydb",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data[0]["name"] == "users"


class TestDescribeEndpoint:
    def test_returns_table_description(self, client):
        resp = client.post(
            "/describe",
            json={
                "config_name": "mysql_dev",
                "instance_name": "db.host.local",
                "schema_name": "mydb",
                "table_name": "users",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data[0]["table_name"] == "users"


class TestScanEndpoints:
    def test_enqueue_returns_202(self, client):
        resp = client.post(
            "/scan",
            json={"config_name": "mysql_dev"},
        )
        assert resp.status_code == 202
        assert resp.json()["data"]["job_id"] == "test-job-id"

    def test_get_scan_job(self, client):
        resp = client.get("/scan/test-job-id")
        assert resp.status_code == 200
        assert resp.json()["data"]["job_id"] == "test-job-id"

    def test_get_scan_job_not_found(self, client):
        with patch("api.src.main.scan_service") as mock_ss:
            mock_ss.get_job.return_value = None
            resp = client.get("/scan/nonexistent")
        assert resp.status_code == 404

    def test_list_scans(self, client):
        resp = client.get("/scans")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_get_scan_with_results(self, client):
        resp = client.get("/scan/test-job-id?include_results=true")
        assert resp.status_code == 200
        assert "results" in resp.json()["data"]
