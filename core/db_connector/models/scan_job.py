from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanScope(BaseModel):
    config_name: Optional[str] = None    # None = all configs
    instance_name: Optional[str] = None  # None = all instances
    schema_name: Optional[str] = None    # None = all schemas
    no_cache: bool = False               # If True, bypass cache during scan


class ScanJob(BaseModel):
    job_id: str
    status: ScanStatus
    scope: ScanScope
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result_count: Optional[int] = None
