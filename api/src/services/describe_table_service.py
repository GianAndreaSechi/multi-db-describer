from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.config_service import ConfigService
from core.db_connector.models import Instance, Schema, Table, TableDescription
from core.db_connector.ai_service import AIDocumentationService
from core.db_connector.storage import get_metadata_store

class DescribeTableService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager):
        self.config_service = config_service
        self.connector_manager = connector_manager

    def describe_table(
        self,
        config_name: Optional[str] = None,
        instance_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        no_cache: bool = False,
        generate_ai_docs: bool = False,
        save_metadata: bool = True,
    ) -> List[TableDescription]:
        all_table_descriptions = []
        config_names_to_process = [config_name] if config_name else self.config_service.get_available_configurations()

        metadata_store = get_metadata_store() if save_metadata else None
        ai_service = AIDocumentationService() if generate_ai_docs else None

        for c_name in config_names_to_process:
            try:
                hosts_to_process = self.config_service.resolve_instance_names(c_name, instance_name, no_cache)

                for host in hosts_to_process:
                    connector = self.config_service._get_connector_for_host(c_name, host)

                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        schemas_to_process = connector.list_schemas(instance_name=host, no_cache=no_cache)

                    for sch in schemas_to_process:
                        tables_to_process = []
                        if table_name:
                            tables_to_process.append(Table(name=table_name, schema_name=sch.name))
                        else:
                            tables_to_process = connector.list_tables(instance_name=host, schema_name=sch.name, no_cache=no_cache)

                        for tbl in tables_to_process:
                            logger.info(f"DescribeTableService: Describing table: {tbl.name} in schema: {sch.name}, host: {host}, config: {c_name}")
                            table_description = connector.describe_table(
                                instance_name=host,
                                schema_name=sch.name,
                                table_name=tbl.name,
                                no_cache=no_cache
                            )
                            all_table_descriptions.append(table_description)

                            desc_dict = table_description.model_dump()
                            ai_doc = None
                            if ai_service:
                                ai_doc = ai_service.generate_table_documentation(desc_dict)

                            if metadata_store:
                                metadata_store.save_table_metadata(
                                    config_name=c_name,
                                    instance_name=host,
                                    schema_name=sch.name,
                                    table_name=tbl.name,
                                    schema_description=desc_dict,
                                    ai_documentation=ai_doc,
                                )

                            logger.info(f"DescribeTableService: Successfully described table: {tbl.name}")
            except Exception as e:
                logger.warning(f"DescribeTableService: Could not describe table for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}, table {table_name if table_name else 'all'}: {e}")
        return all_table_descriptions
