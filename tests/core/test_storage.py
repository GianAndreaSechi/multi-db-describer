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
