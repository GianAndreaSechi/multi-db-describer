"""
JobStore: Redis-backed persistence for async scan jobs.

Keys used (all prefixed with CACHE_KEY_PREFIX env var):
  {prefix}:scan:job:{job_id}      → Hash  (job metadata, flat string fields)
  {prefix}:scan:results:{job_id}  → List  (serialized TableDescription items)
  {prefix}:scan:jobs              → Sorted Set (job_id scored by creation timestamp)
  {prefix}:scan:queue             → Stream (job messages for workers)

Serialization contract:
  ScanJob  ──→  _to_fields()   ──→  Redis Hash (flat strings)
  Redis Hash ──→ _from_fields() ──→  ScanJob
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import redis
from loguru import logger

from core.db_connector.models.scan_job import ScanJob, ScanScope, ScanStatus

STREAM_KEY_SUFFIX = "scan:queue"
JOB_KEY_SUFFIX = "scan:job"
RESULTS_KEY_SUFFIX = "scan:results"
JOBS_SET_SUFFIX = "scan:jobs"

CONSUMER_GROUP = "scan-workers"
RESULTS_TTL = int(os.getenv("SCAN_RESULTS_TTL_SECONDS", 86400 * 7))  # 7 days default


class JobStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "multi-db-connector",
    ):
        self.prefix = prefix
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._ensure_stream_group()

    # ------------------------------------------------------------------
    # Serialization — single source of truth for model ↔ Redis mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_fields(job: ScanJob) -> Dict[str, str]:
        """Flatten a ScanJob into Redis Hash-compatible string fields."""
        def _str(val) -> str:
            return val.isoformat() if isinstance(val, datetime) else (str(val) if val is not None else "")

        return {
            "job_id":        job.job_id,
            "status":        job.status.value,
            "config_name":   job.scope.config_name or "",
            "instance_name": job.scope.instance_name or "",
            "schema_name":   job.scope.schema_name or "",
            "no_cache":      "true" if job.scope.no_cache else "false",
            "created_at":    _str(job.created_at),
            "started_at":    _str(job.started_at),
            "completed_at":  _str(job.completed_at),
            "error":         job.error or "",
            "result_count":  str(job.result_count) if job.result_count is not None else "",
        }

    @staticmethod
    def _from_fields(fields: Dict[str, str]) -> ScanJob:
        """Reconstruct a ScanJob from Redis Hash string fields."""
        def _dt(val: str) -> Optional[datetime]:
            return datetime.fromisoformat(val) if val else None

        return ScanJob(
            job_id=fields["job_id"],
            status=ScanStatus(fields["status"]),
            scope=ScanScope(
                config_name=fields.get("config_name") or None,
                instance_name=fields.get("instance_name") or None,
                schema_name=fields.get("schema_name") or None,
                no_cache=fields.get("no_cache") == "true",
            ),
            created_at=_dt(fields.get("created_at", "")),
            started_at=_dt(fields.get("started_at", "")),
            completed_at=_dt(fields.get("completed_at", "")),
            error=fields.get("error") or None,
            result_count=int(fields["result_count"]) if fields.get("result_count") else None,
        )

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _k(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"

    def _job_key(self, job_id: str) -> str:
        return self._k(f"{JOB_KEY_SUFFIX}:{job_id}")

    def _results_key(self, job_id: str) -> str:
        return self._k(f"{RESULTS_KEY_SUFFIX}:{job_id}")

    def _stream_key(self) -> str:
        return self._k(STREAM_KEY_SUFFIX)

    def _jobs_set_key(self) -> str:
        return self._k(JOBS_SET_SUFFIX)

    # ------------------------------------------------------------------
    # Stream / queue
    # ------------------------------------------------------------------

    def _ensure_stream_group(self):
        try:
            self.r.xgroup_create(self._stream_key(), CONSUMER_GROUP, id="0", mkstream=True)
            logger.info(f"JobStore: Created consumer group '{CONSUMER_GROUP}' on stream '{self._stream_key()}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                pass  # group already exists — expected on restart
            else:
                logger.error(f"JobStore: Could not create consumer group: {e}")
        except redis.exceptions.ConnectionError as e:
            # Redis not reachable at startup — log and continue.
            # Operations will fail at call time with a clear ConnectionError.
            logger.warning(f"JobStore: Redis not reachable during startup — stream group not created: {e}")

    def enqueue(self, scope: ScanScope) -> ScanJob:
        job = ScanJob(
            job_id=str(uuid.uuid4()),
            status=ScanStatus.PENDING,
            scope=scope,
            created_at=datetime.now(timezone.utc),
        )
        fields = self._to_fields(job)

        pipe = self.r.pipeline()
        pipe.hset(self._job_key(job.job_id), mapping=fields)
        pipe.expire(self._job_key(job.job_id), RESULTS_TTL)
        pipe.zadd(self._jobs_set_key(), {job.job_id: job.created_at.timestamp()})
        pipe.xadd(self._stream_key(), {
            "job_id":        job.job_id,
            "config_name":   fields["config_name"],
            "instance_name": fields["instance_name"],
            "schema_name":   fields["schema_name"],
            "no_cache":      fields["no_cache"],
        })
        pipe.execute()

        logger.info(f"JobStore: Enqueued scan job {job.job_id} scope={scope}")
        return job

    # ------------------------------------------------------------------
    # Job status updates (used by worker) — targeted partial hset
    # ------------------------------------------------------------------

    def mark_running(self, job_id: str):
        self.r.hset(self._job_key(job_id), mapping={
            "status":     ScanStatus.RUNNING.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    def mark_completed(self, job_id: str, result_count: int):
        self.r.hset(self._job_key(job_id), mapping={
            "status":       ScanStatus.COMPLETED.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result_count": str(result_count),
        })

    def mark_failed(self, job_id: str, error: str):
        self.r.hset(self._job_key(job_id), mapping={
            "status":       ScanStatus.FAILED.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error":        error,
        })

    # ------------------------------------------------------------------
    # Results (worker appends, API reads)
    # ------------------------------------------------------------------

    def append_result(self, job_id: str, table_description_dict: Dict[str, Any]):
        self.r.rpush(self._results_key(job_id), json.dumps(table_description_dict))

    def get_results(self, job_id: str) -> List[Dict[str, Any]]:
        raw = self.r.lrange(self._results_key(job_id), 0, -1)
        return [json.loads(item) for item in raw]

    # ------------------------------------------------------------------
    # Job retrieval
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[ScanJob]:
        fields = self.r.hgetall(self._job_key(job_id))
        if not fields:
            return None
        return self._from_fields(fields)

    def list_jobs(self, limit: int = 50) -> List[ScanJob]:
        """Returns most recent `limit` jobs (newest first)."""
        job_ids = self.r.zrevrange(self._jobs_set_key(), 0, limit - 1)
        jobs = []
        for jid in job_ids:
            job = self.get_job(jid)
            if job:
                jobs.append(job)
        return jobs

    # ------------------------------------------------------------------
    # Stream consumer (used by worker)
    # ------------------------------------------------------------------

    def read_pending(self, consumer_name: str, count: int = 1, block_ms: int = 5000):
        """Blocking read of new (undelivered) messages from the stream."""
        return self.r.xreadgroup(
            CONSUMER_GROUP,
            consumer_name,
            {self._stream_key(): ">"},
            count=count,
            block=block_ms,
        )

    def reclaim_abandoned(self, consumer_name: str, min_idle_ms: int = 30000, count: int = 10) -> list:
        """
        Reclaim messages that were delivered to a now-dead consumer and never acknowledged.
        Called on each poll cycle to recover from worker crashes/restarts.

        Returns a list of (message_id, data) tuples ready to process.
        """
        try:
            pending = self.r.xpending_range(
                self._stream_key(), CONSUMER_GROUP,
                min="-", max="+", count=count,
            )
            if not pending:
                return []

            idle_ids = [
                p["message_id"]
                for p in pending
                if p.get("time_since_delivered", 0) >= min_idle_ms
                   and p.get("name") != consumer_name  # don't reclaim own messages
            ]
            if not idle_ids:
                return []

            claimed = self.r.xclaim(
                self._stream_key(), CONSUMER_GROUP, consumer_name,
                min_idle_time=min_idle_ms, message_ids=idle_ids,
            )
            if claimed:
                logger.info(f"JobStore: reclaimed {len(claimed)} abandoned message(s)")
            return claimed or []
        except Exception as e:
            logger.warning(f"JobStore: reclaim_abandoned failed: {e}")
            return []

    def ack(self, message_id: str):
        self.r.xack(self._stream_key(), CONSUMER_GROUP, message_id)
