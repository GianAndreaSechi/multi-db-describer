from typing import Optional
from pydantic import BaseModel, Field


class DescribeTableRequest(BaseModel):
    config_name: Optional[str] = Field(
        default=None,
        description="Configured database target name, e.g. 'mysql_publishers_dev'.",
    )
    instance_name: Optional[str] = Field(
        default=None,
        description="Database instance returned by list_instances. For MySQL this is the configured host.",
    )
    schema_name: Optional[str] = Field(
        default=None,
        description="Schema/database name, e.g. 'quality_checks'.",
    )
    table_name: Optional[str] = Field(default=None, description="Table name to describe.")
    generate_ai_docs: bool = Field(default=False, description="Generate AI documentation.")
    save_metadata: bool = Field(default=True, description="Persist generated metadata.")
    only_if_changed: bool = Field(
        default=False,
        description="When save_metadata=True, skip writing if schema_description is unchanged. Preserves updated_at and avoids noise.",
    )
    save_markdown: bool = Field(
        default=False,
        description="Save an LLM-friendly Markdown document alongside persisted JSON metadata.",
    )
