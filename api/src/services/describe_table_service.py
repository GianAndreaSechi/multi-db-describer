from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import Instance, Schema, Table, TableDescription
from api.src.services.config_service import ConfigService
from api.src.services.instance_service import InstanceService
from api.src.services.schema_service import SchemaService
from api.src.services.table_service import TableService # New import

class DescribeTableService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager, instance_service: InstanceService, schema_service: SchemaService, table_service: TableService):
        self.config_service = config_service
        self.connector_manager = connector_manager
        self.instance_service = instance_service
        self.schema_service = schema_service
        self.table_service = table_service

    def describe_table(self, config_name: Optional[str] = None, instance_name: Optional[str] = None, schema_name: Optional[str] = None, table_name: Optional[str] = None) -> List[TableDescription]:
        all_table_descriptions = []
        config_names_to_process = [config_name] if config_name else self.config_service.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self.config_service._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    instances_for_config = self.instance_service.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        schemas_for_instance = self.schema_service.list_schemas(config_name=c_name, instance_name=inst.name)
                        schemas_to_process.extend(schemas_for_instance)

                    for sch in schemas_to_process:
                        tables_to_process = []
                        if table_name:
                            tables_to_process.append(Table(name=table_name))
                        else:
                            tables_for_schema = self.table_service.list_tables(config_name=c_name, instance_name=inst.name, schema_name=sch.name)
                            tables_to_process.extend(tables_for_schema)

                        for tbl in tables_to_process:
                            logger.info(f"DescribeTableService: Describing table: {tbl.name} in schema: {sch.name}, instance: {inst.name}, config: {c_name}")
                            connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                            table_description = connector.describe_table(
                                instance_name=inst.name,
                                schema_name=sch.name,
                                table_name=tbl.name,
                            )
                            all_table_descriptions.append(table_description)
                            logger.info(f"DescribeTableService: Successfully described table: {tbl.name}")
            except Exception as e:
                logger.warning(f"DescribeTableService: Could not describe table for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}, table {table_name if table_name else 'all'}: {e}")
        return all_table_descriptions
