import time
import pytest
from core.db_connector.storage import FileMetadataStore, build_metadata_key


@pytest.fixture
def store(tmp_path):
    return FileMetadataStore(base_dir=str(tmp_path))


SCHEMA_DESC = {
    "instance_name": "db.host.local",
    "schema_name": "mydb",
    "table_name": "users",
    "columns": [{"name": "id", "data_type": "int"}],
}


class TestBuildMetadataKey:
    def test_composite_key(self):
        key = build_metadata_key("cfg", "inst", "sch", "tbl")
        assert key == "cfg::inst::sch::tbl"


class TestFileMetadataStoreSanitize:
    def test_replaces_slash(self, store):
        result = store._sanitize("a/b")
        assert "/" not in result

    def test_replaces_colon(self, store):
        result = store._sanitize("host:3306")
        assert ":" not in result

    def test_replaces_star_and_question(self, store):
        result = store._sanitize("tab*le?name")
        assert "*" not in result
        assert "?" not in result

    def test_preserves_dot(self, store):
        result = store._sanitize("db.host.local")
        assert result == "db.host.local"

    def test_preserves_hyphen_and_underscore(self, store):
        result = store._sanitize("my-config_name")
        assert result == "my-config_name"


class TestFileMetadataStoreGetSave:
    def test_get_returns_none_for_missing(self, store):
        assert store.get_table_metadata("cfg", "inst", "sch", "tbl") is None

    def test_save_and_get_roundtrip(self, store):
        saved = store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")

        assert loaded is not None
        assert loaded["table_name"] == "users"
        assert loaded["schema_description"] == SCHEMA_DESC
        assert loaded["ai_documentation"] is None
        assert "updated_at" in loaded
        assert loaded["metadata_key"] == "cfg::inst::sch::users"

    def test_save_with_ai_doc(self, store):
        ai_doc = {"summary": "User table", "column_descriptions": {"id": "Primary key"}}
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, ai_documentation=ai_doc)
        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")
        assert loaded["ai_documentation"] == ai_doc

    def test_schema_update_preserves_existing_ai_doc(self, store):
        ai_doc = {"summary": "Preserved", "column_descriptions": {}}
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, ai_documentation=ai_doc)

        new_schema = {**SCHEMA_DESC, "columns": [{"name": "id", "data_type": "bigint"}]}
        store.save_table_metadata("cfg", "inst", "sch", "users", new_schema, ai_documentation=None)

        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")
        assert loaded["ai_documentation"] == ai_doc
        assert loaded["schema_description"]["columns"][0]["data_type"] == "bigint"

    def test_ai_doc_can_be_overwritten(self, store):
        first = {"summary": "First"}
        second = {"summary": "Second"}
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, ai_documentation=first)
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, ai_documentation=second)
        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")
        assert loaded["ai_documentation"]["summary"] == "Second"

    def test_special_chars_in_names_do_not_raise(self, store):
        store.save_table_metadata("cfg:1", "host:3306", "db/schema", "tab*le", SCHEMA_DESC)
        loaded = store.get_table_metadata("cfg:1", "host:3306", "db/schema", "tab*le")
        assert loaded is not None

    def test_creates_nested_directories(self, store, tmp_path):
        store.save_table_metadata("c", "i", "s", "t", SCHEMA_DESC)
        expected = tmp_path / "c" / "i" / "s" / "t.json"
        assert expected.exists()


class TestOnlyIfChanged:
    def test_unchanged_schema_returns_unchanged_flag(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        result = store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, only_if_changed=True)
        assert result.get("_unchanged") is True

    def test_unchanged_schema_does_not_update_file(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        original = store.get_table_metadata("cfg", "inst", "sch", "users")["updated_at"]
        time.sleep(0.01)
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC, only_if_changed=True)
        reloaded = store.get_table_metadata("cfg", "inst", "sch", "users")["updated_at"]
        assert original == reloaded

    def test_changed_schema_writes_with_flag(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        new_schema = {**SCHEMA_DESC, "columns": [{"name": "id", "data_type": "bigint"}]}
        result = store.save_table_metadata("cfg", "inst", "sch", "users", new_schema, only_if_changed=True)
        assert "_unchanged" not in result
        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")
        assert loaded["schema_description"]["columns"][0]["data_type"] == "bigint"

    def test_first_save_always_writes(self, store):
        result = store.save_table_metadata("cfg", "inst", "sch", "new_table", SCHEMA_DESC, only_if_changed=True)
        assert "_unchanged" not in result
        assert store.get_table_metadata("cfg", "inst", "sch", "new_table") is not None


class TestMarkdownMetadata:
    def test_saves_llm_friendly_markdown_companion(self, store, tmp_path):
        ai_doc = {
            "summary": "Stores application users.",
            "column_descriptions": {"id": "Primary identifier."},
        }
        store.save_table_metadata(
            "cfg", "inst", "sch", "users", SCHEMA_DESC,
            ai_documentation=ai_doc,
            save_markdown=True,
        )

        markdown = (tmp_path / "cfg" / "inst" / "sch" / "users.md").read_text()
        assert "# sch.users" in markdown
        assert "Stores application users." in markdown
        assert "| id | int |  | Primary identifier. |" in markdown

    def test_creates_markdown_when_unchanged_metadata_is_skipped(self, store, tmp_path):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        store.save_table_metadata(
            "cfg", "inst", "sch", "users", SCHEMA_DESC,
            only_if_changed=True,
            save_markdown=True,
        )
        assert (tmp_path / "cfg" / "inst" / "sch" / "users.md").exists()


class TestCustomFieldCarryForward:
    def test_custom_fields_preserved_on_resave(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        store.update_table_metadata("inst", "sch", "users", {"owner": "data-team", "tags": ["pii"]})

        new_schema = {**SCHEMA_DESC, "columns": [{"name": "id", "data_type": "bigint"}]}
        store.save_table_metadata("cfg", "inst", "sch", "users", new_schema)

        loaded = store.get_table_metadata("cfg", "inst", "sch", "users")
        assert loaded["owner"] == "data-team"
        assert loaded["tags"] == ["pii"]

    def test_system_key_updated_at_regenerated_on_resave(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "users", SCHEMA_DESC)
        old_ts = store.get_table_metadata("cfg", "inst", "sch", "users")["updated_at"]
        time.sleep(0.01)
        new_schema = {**SCHEMA_DESC, "columns": [{"name": "id", "data_type": "bigint"}]}
        store.save_table_metadata("cfg", "inst", "sch", "users", new_schema)
        new_ts = store.get_table_metadata("cfg", "inst", "sch", "users")["updated_at"]
        assert new_ts != old_ts

    def test_multiple_custom_fields_all_preserved(self, store):
        store.save_table_metadata("cfg", "inst", "sch", "orders", SCHEMA_DESC)
        store.update_table_metadata("inst", "sch", "orders", {
            "owner": "billing",
            "notes": "Replicated every 6h",
            "data_classification": "confidential",
        })
        store.save_table_metadata("cfg", "inst", "sch", "orders", SCHEMA_DESC)

        loaded = store.get_table_metadata("cfg", "inst", "sch", "orders")
        assert loaded["owner"] == "billing"
        assert loaded["notes"] == "Replicated every 6h"
        assert loaded["data_classification"] == "confidential"


class TestListInstances:
    def test_empty_store_returns_empty(self, store):
        result = store.list_instances()
        assert result["items"] == []
        assert result["total"] == 0
        assert result["pages"] == 0

    def test_lists_instances_after_save(self, store):
        store.save_table_metadata("cfg", "host_a", "sch", "tbl", SCHEMA_DESC)
        store.save_table_metadata("cfg", "host_b", "sch", "tbl", SCHEMA_DESC)
        result = store.list_instances()
        assert "host_a" in result["items"]
        assert "host_b" in result["items"]
        assert result["total"] == 2

    def test_deduplicates_across_configs(self, store):
        store.save_table_metadata("cfg1", "host_x", "sch", "tbl", SCHEMA_DESC)
        store.save_table_metadata("cfg2", "host_x", "sch", "tbl", SCHEMA_DESC)
        result = store.list_instances()
        assert result["items"].count("host_x") == 1

    def test_pagination(self, store):
        for i in range(5):
            store.save_table_metadata("cfg", f"host_{i}", "sch", "tbl", SCHEMA_DESC)
        page1 = store.list_instances(page=1, page_size=3)
        page2 = store.list_instances(page=2, page_size=3)
        assert len(page1["items"]) == 3
        assert len(page2["items"]) == 2
        assert page1["pages"] == 2
        assert page1["total"] == 5


class TestListDatabases:
    def test_returns_databases_for_instance(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "tbl", SCHEMA_DESC)
        store.save_table_metadata("cfg", "host_a", "db2", "tbl", SCHEMA_DESC)
        result = store.list_databases("host_a")
        assert "db1" in result["items"]
        assert "db2" in result["items"]
        assert result["total"] == 2

    def test_empty_for_unknown_instance(self, store):
        result = store.list_databases("nonexistent")
        assert result["total"] == 0
        assert result["items"] == []

    def test_does_not_include_other_instances(self, store):
        store.save_table_metadata("cfg", "host_a", "db_a", "tbl", SCHEMA_DESC)
        store.save_table_metadata("cfg", "host_b", "db_b", "tbl", SCHEMA_DESC)
        result = store.list_databases("host_a")
        assert "db_b" not in result["items"]


class TestListTablesMeta:
    def test_returns_tables_for_instance_database(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        store.save_table_metadata("cfg", "host_a", "db1", "orders", SCHEMA_DESC)
        result = store.list_tables_metadata("host_a", "db1")
        assert "users" in result["items"]
        assert "orders" in result["items"]
        assert result["total"] == 2

    def test_empty_for_unknown_database(self, store):
        result = store.list_tables_metadata("host_a", "nonexistent_db")
        assert result["total"] == 0

    def test_does_not_include_other_databases(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        store.save_table_metadata("cfg", "host_a", "db2", "orders", SCHEMA_DESC)
        result = store.list_tables_metadata("host_a", "db1")
        assert "orders" not in result["items"]


class TestFindTableMetadata:
    def test_finds_table_across_configs(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        result = store.find_table_metadata("host_a", "db1", "users")
        assert result is not None
        assert result["table_name"] == "users"

    def test_returns_none_for_missing_table(self, store):
        assert store.find_table_metadata("no_host", "no_db", "no_table") is None

    def test_returns_first_match_across_multiple_configs(self, store):
        store.save_table_metadata("cfg1", "host_a", "db1", "users", SCHEMA_DESC)
        store.save_table_metadata("cfg2", "host_a", "db1", "users", SCHEMA_DESC)
        result = store.find_table_metadata("host_a", "db1", "users")
        assert result is not None


class TestUpdateTableMetadata:
    def test_merges_custom_fields(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        result = store.update_table_metadata("host_a", "db1", "users", {"owner": "team-a", "tags": ["pii"]})
        assert result["owner"] == "team-a"
        assert result["tags"] == ["pii"]

    def test_protected_fields_are_not_overwritten(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        result = store.update_table_metadata("host_a", "db1", "users", {
            "metadata_key": "hacked",
            "config_name": "hacked",
            "instance_name": "hacked",
            "schema_name": "hacked",
            "table_name": "hacked",
            "updated_at": "hacked",
            "owner": "team-a",
        })
        assert result["owner"] == "team-a"
        assert result["metadata_key"] != "hacked"
        assert result["config_name"] == "cfg"
        assert result["instance_name"] == "host_a"
        assert result["table_name"] == "users"

    def test_returns_none_for_missing_table(self, store):
        result = store.update_table_metadata("no_host", "no_db", "no_table", {"owner": "x"})
        assert result is None

    def test_persists_update_to_disk(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        store.update_table_metadata("host_a", "db1", "users", {"owner": "team-a"})
        loaded = store.get_table_metadata("cfg", "host_a", "db1", "users")
        assert loaded["owner"] == "team-a"

    def test_updates_updated_at(self, store):
        store.save_table_metadata("cfg", "host_a", "db1", "users", SCHEMA_DESC)
        original_ts = store.get_table_metadata("cfg", "host_a", "db1", "users")["updated_at"]
        time.sleep(0.01)
        store.update_table_metadata("host_a", "db1", "users", {"owner": "team-a"})
        updated = store.get_table_metadata("cfg", "host_a", "db1", "users")["updated_at"]
        assert updated != original_ts
