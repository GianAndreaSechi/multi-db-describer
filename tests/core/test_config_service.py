import pytest
from unittest.mock import MagicMock, patch
from core.db_connector.config_service import ConfigService
from core.db_connector.models import Instance, Schema

DB_CONFIGS = {
    "mysql_dev": {
        "connector_type": "mysql",
        "connection_params": {
            "hosts": [{"host": "mysql-dev.local", "user": "root", "password": ""}]
        },
    },
    "pg_dev": {
        "connector_type": "postgres",
        "connection_params": {
            "host": "pg-dev.local",
            "user": "postgres",
            "password": "",
            "database": "mydb",
        },
    },
}


@pytest.fixture
def mock_connector():
    c = MagicMock()
    c.list_instances.return_value = [Instance(name="mysql-dev.local")]
    c.list_schemas.return_value = [Schema(name="mydb")]
    return c


@pytest.fixture
def connector_manager(mock_connector):
    mgr = MagicMock()
    mgr.get_connector.return_value = mock_connector
    return mgr


@pytest.fixture
def config_service(connector_manager):
    with patch(
        "core.db_connector.config_service.get_db_configurations",
        return_value=DB_CONFIGS,
    ):
        return ConfigService(connector_manager)


class TestGetAvailableConfigurations:
    def test_returns_config_names(self, config_service):
        names = config_service.get_available_configurations()
        assert set(names) == {"mysql_dev", "pg_dev"}


class TestGetConnectorDetails:
    def test_raises_for_unknown_config(self, config_service):
        with pytest.raises(ValueError, match="not found"):
            config_service._get_connector_details("nonexistent")

    def test_returns_type_and_params(self, config_service):
        details = config_service._get_connector_details("mysql_dev")
        assert details["connector_type"] == "mysql"
        assert "connection_params" in details


class TestGetHosts:
    def test_returns_multi_host_values(self, config_service):
        assert config_service._get_hosts("mysql_dev") == ["mysql-dev.local"]

    def test_returns_flat_host_value(self, config_service):
        assert config_service._get_hosts("pg_dev") == ["pg-dev.local"]


class TestConfigurationMatchesInstance:
    def test_matches_only_the_owning_configuration(self, config_service):
        assert config_service.configuration_matches_instance("mysql_dev", "mysql-dev.local") is True
        assert config_service.configuration_matches_instance("pg_dev", "mysql-dev.local") is False

    def test_resolves_configuration_from_instance(self, config_service):
        assert config_service.resolve_configurations_for_instance("mysql-dev.local") == ["mysql_dev"]


class TestListInstances:
    def test_multi_host_config(self, config_service, mock_connector):
        instances = config_service.list_instances("mysql_dev")
        assert len(instances) == 1
        assert instances[0].name == "mysql-dev.local"

    def test_flat_config(self, config_service, mock_connector):
        mock_connector.list_instances.return_value = [Instance(name="pg-dev.local")]
        instances = config_service.list_instances("pg_dev")
        assert instances[0].name == "pg-dev.local"

    def test_no_cache_propagated(self, config_service, mock_connector):
        config_service.list_instances("mysql_dev", no_cache=True)
        mock_connector.list_instances.assert_called_once_with(no_cache=True)


class TestResolveInstanceNames:
    def test_returns_explicit_instance(self, config_service):
        names = config_service.resolve_instance_names("mysql_dev", instance_name="mysql-dev.local")
        assert names == ["mysql-dev.local"]

    def test_resolves_all_when_none(self, config_service, mock_connector):
        mock_connector.list_instances.return_value = [
            Instance(name="h1"),
            Instance(name="h2"),
        ]
        names = config_service.resolve_instance_names("mysql_dev", instance_name=None)
        assert set(names) == {"h1", "h2"}


class TestGetConnectorForHost:
    def test_multi_host_finds_correct_host(self, config_service, connector_manager):
        config_service._get_connector_for_host("mysql_dev", "mysql-dev.local")
        connector_manager.get_connector.assert_called_once_with(
            "mysql", {"host": "mysql-dev.local", "user": "root", "password": ""}
        )

    def test_flat_config_ignores_host_lookup(self, config_service, connector_manager):
        config_service._get_connector_for_host("pg_dev", "pg-dev.local")
        call_args = connector_manager.get_connector.call_args
        assert call_args[0][0] == "postgres"

    def test_raises_for_unknown_host_in_multi_host(self, config_service):
        with pytest.raises(ValueError, match="not found"):
            config_service._get_connector_for_host("mysql_dev", "unknown-host")


class TestTestConnection:
    def test_succeeds_when_instances_reachable(self, config_service, mock_connector):
        result = config_service.test_connection("mysql_dev")
        assert "Successfully connected" in result["message"]

    def test_propagates_no_cache(self, config_service, mock_connector):
        config_service.test_connection("mysql_dev")
        mock_connector.list_instances.assert_called_once_with(no_cache=True)
