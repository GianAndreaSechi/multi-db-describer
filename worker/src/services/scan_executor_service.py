from typing import Optional
from loguru import logger

from core.db_connector.config_service import ConfigService
from core.db_connector.job_store import JobStore
from core.db_connector.models import Schema
from core.db_connector.ai_service import AIDocumentationService
from core.db_connector.storage import get_metadata_store


class ScanExecutorService:
    def __init__(self, job_store: JobStore, config_service: ConfigService):
        self.job_store = job_store
        self.config_service = config_service

    def execute(
        self,
        job_id: str,
        config_name: Optional[str],
        instance_name: Optional[str],
        schema_name: Optional[str],
        no_cache: bool = False,
        generate_ai_docs: bool = False,
        save_metadata: bool = True,
    ) -> int:
        """
        Scans tables according to the given scope, stores each TableDescription
        in Redis, optionally generates AI documentation, persists metadata to disk/store,
        and returns the total count of described tables.
        """
        count = 0
        config_names = (
            [config_name] if config_name
            else self.config_service.get_available_configurations()
        )

        metadata_store = get_metadata_store() if save_metadata else None
        ai_service = AIDocumentationService() if generate_ai_docs else None

        for c_name in config_names:
            try:
                hosts = self.config_service.resolve_instance_names(c_name, instance_name, no_cache)

                for host in hosts:
                    connector = self.config_service._get_connector_for_host(c_name, host)

                    schemas = (
                        [Schema(name=schema_name)]
                        if schema_name
                        else connector.list_schemas(instance_name=host, no_cache=no_cache)
                    )

                    for sch in schemas:
                        tables = connector.list_tables(
                            instance_name=host,
                            schema_name=sch.name,
                            no_cache=no_cache
                        )

                        for tbl in tables:
                            logger.info(
                                f"ScanExecutorService [{job_id}]: "
                                f"{c_name}/{host}/{sch.name}/{tbl.name} (no_cache={no_cache})"
                            )
                            try:
                                desc = connector.describe_table(
                                    instance_name=host,
                                    schema_name=sch.name,
                                    table_name=tbl.name,
                                    no_cache=no_cache,
                                )
                                desc_dict = desc.model_dump()
                                self.job_store.append_result(job_id, desc_dict)

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

                                count += 1
                            except Exception as e:
                                logger.warning(
                                    f"ScanExecutorService [{job_id}]: failed to describe "
                                    f"{sch.name}.{tbl.name}: {e}"
                                )
            except Exception as e:
                logger.warning(
                    f"ScanExecutorService [{job_id}]: error processing config {c_name}: {e}"
                )

        return count

