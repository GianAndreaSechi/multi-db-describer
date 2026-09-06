from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from core.db_connector.exporting import ExportOptions


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ScanScope(BaseModel):
    config_name: Optional[str] = None    # None = all configs
    instance_name: Optional[str] = None  # None = all instances
    schema_name: Optional[str] = None    # None = all schemas
    no_cache: bool = False               # If True, bypass cache during scan
    generate_ai_docs: bool = False       # If True, generate AI documentation via LiteLLM
    save_metadata: bool = True           # If True, save/update JSON metadata
    only_if_changed: bool = False        # If True, skip unchanged metadata writes
    export_options: ExportOptions = Field(default_factory=ExportOptions)



class ScanJob(BaseModel):
    job_id: str
    status: ScanStatus
    scope: ScanScope
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result_count: Optional[int] = None
