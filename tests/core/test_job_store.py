import pytest
import fakeredis
from unittest.mock import patch
from core.db_connector.job_store import JobStore
from core.db_connector.models.scan_job import ScanScope, ScanStatus
from core.db_connector.exporting import ExportFormat, ExportOptions


@pytest.fixture
def job_store():
    fake = fakeredis.FakeRedis(decode_responses=True)
    with patch("core.db_connector.job_store.redis.Redis", return_value=fake):
        store = JobStore(prefix="test")
    return store


SCOPE = ScanScope(config_name="cfg", instance_name="inst", schema_name="sch")
SCOPE_FULL = ScanScope(
    config_name="cfg",
    instance_name="inst",
    schema_name="sch",
    no_cache=True,
    generate_ai_docs=True,
    save_metadata=False,
    export_options=ExportOptions(formats=[ExportFormat.OKF], preformat=False),
)


class TestEnqueue:
    def test_returns_pending_job(self, job_store):
        job = job_store.enqueue(SCOPE)
        assert job.status == ScanStatus.PENDING
        assert job.job_id

    def test_job_retrievable_after_enqueue(self, job_store):
        job = job_store.enqueue(SCOPE)
        fetched = job_store.get_job(job.job_id)
        assert fetched is not None
        assert fetched.job_id == job.job_id
        assert fetched.status == ScanStatus.PENDING

    def test_scope_preserved(self, job_store):
        job = job_store.enqueue(SCOPE_FULL)
        fetched = job_store.get_job(job.job_id)
        assert fetched.scope.config_name == "cfg"
        assert fetched.scope.no_cache is True
        assert fetched.scope.generate_ai_docs is True
        assert fetched.scope.save_metadata is False
        assert fetched.scope.export_options.formats == [ExportFormat.OKF]
        assert fetched.scope.export_options.preformat is False

    def test_default_exports_preserved(self, job_store):
        job = job_store.enqueue(SCOPE)
        fetched = job_store.get_job(job.job_id)
        assert fetched.scope.export_options.formats == [ExportFormat.MARKDOWN, ExportFormat.OKF]
        assert fetched.scope.export_options.preformat is True

    def test_stream_contains_export_options(self, job_store):
        job_store.enqueue(SCOPE_FULL)
        messages = job_store.r.xrange(job_store._stream_key())
        fields = messages[-1][1]
        assert fields["export_formats"] == '["okf"]'
        assert fields["export_preformat"] == "false"

    def test_job_appears_in_list(self, job_store):
        job = job_store.enqueue(SCOPE)
        jobs = job_store.list_jobs()
        assert any(j.job_id == job.job_id for j in jobs)


class TestStatusTransitions:
    def test_mark_running(self, job_store):
        job = job_store.enqueue(SCOPE)
        job_store.mark_running(job.job_id)
        fetched = job_store.get_job(job.job_id)
        assert fetched.status == ScanStatus.RUNNING
        assert fetched.started_at is not None

    def test_mark_completed(self, job_store):
        job = job_store.enqueue(SCOPE)
        job_store.mark_completed(job.job_id, result_count=42)
        fetched = job_store.get_job(job.job_id)
        assert fetched.status == ScanStatus.COMPLETED
        assert fetched.result_count == 42
        assert fetched.completed_at is not None

    def test_mark_failed(self, job_store):
        job = job_store.enqueue(SCOPE)
        job_store.mark_failed(job.job_id, error="something went wrong")
        fetched = job_store.get_job(job.job_id)
        assert fetched.status == ScanStatus.FAILED
        assert fetched.error == "something went wrong"

    def test_mark_partial(self, job_store):
        job = job_store.enqueue(SCOPE)
        job_store.mark_partial(job.job_id, result_count=5, error="partial error")
        fetched = job_store.get_job(job.job_id)
        assert fetched.status == ScanStatus.PARTIAL
        assert fetched.result_count == 5
        assert "partial error" in fetched.error


class TestResults:
    def test_append_and_get_results(self, job_store):
        job = job_store.enqueue(SCOPE)
        job_store.append_result(job.job_id, {"table": "users", "columns": []})
        job_store.append_result(job.job_id, {"table": "orders", "columns": []})
        results = job_store.get_results(job.job_id)
        assert len(results) == 2
        assert results[0]["table"] == "users"
        assert results[1]["table"] == "orders"

    def test_empty_results_for_new_job(self, job_store):
        job = job_store.enqueue(SCOPE)
        assert job_store.get_results(job.job_id) == []


class TestListJobs:
    def test_returns_newest_first(self, job_store):
        j1 = job_store.enqueue(SCOPE)
        j2 = job_store.enqueue(SCOPE)
        jobs = job_store.list_jobs(limit=10)
        ids = [j.job_id for j in jobs]
        assert ids.index(j2.job_id) < ids.index(j1.job_id)

    def test_limit_respected(self, job_store):
        for _ in range(5):
            job_store.enqueue(SCOPE)
        jobs = job_store.list_jobs(limit=3)
        assert len(jobs) == 3

    def test_get_job_returns_none_for_unknown(self, job_store):
        assert job_store.get_job("nonexistent-id") is None


class TestNoneScope:
    def test_none_scope_fields_preserved(self, job_store):
        scope = ScanScope(config_name=None, instance_name=None, schema_name=None)
        job = job_store.enqueue(scope)
        fetched = job_store.get_job(job.job_id)
        assert fetched.scope.config_name is None
        assert fetched.scope.instance_name is None
        assert fetched.scope.schema_name is None
