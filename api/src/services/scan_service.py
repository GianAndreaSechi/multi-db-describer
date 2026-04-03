from typing import Optional, List, Dict, Any

from core.db_connector.models.scan_job import ScanJob, ScanScope
from core.db_connector.job_store import JobStore


class ScanService:
    def __init__(self, job_store: JobStore):
        self.job_store = job_store

    def enqueue_scan(
        self,
        config_name: Optional[str],
        instance_name: Optional[str],
        schema_name: Optional[str],
        no_cache: bool = False,
    ) -> ScanJob:
        scope = ScanScope(
            config_name=config_name,
            instance_name=instance_name,
            schema_name=schema_name,
            no_cache=no_cache,
        )
        return self.job_store.enqueue(scope)

    def get_job(self, job_id: str) -> Optional[ScanJob]:
        return self.job_store.get_job(job_id)

    def get_job_results(self, job_id: str) -> List[Dict[str, Any]]:
        return self.job_store.get_results(job_id)

    def list_jobs(self, limit: int = 50) -> List[ScanJob]:
        return self.job_store.list_jobs(limit)
