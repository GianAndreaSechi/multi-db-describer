from typing import Optional
from pydantic import BaseModel, Field


class DescribeTableRequest(BaseModel):
    config_name: Optional[str] = Field(
        default=None,
        description="Configured database target name, e.g. 'mysql_publishers_dev'.",
    )
    instance_name: Optional[str] = Field(
        default=None,
        description=(
            "Database instance returned by list_instances. For MySQL this is "
            "the configured MySQL host. Omit to describe tables from all instances in config_name."
        ),
    )
    schema_name: Optional[str] = Field(
        default=None,
        description="Schema/database name, e.g. 'quality_checks'.",
    )
    table_name: Optional[str] = Field(
        default=None,
        description="Table name to describe. Omit to describe all tables in the selected schema.",
    )
    generate_ai_docs: bool = Field(
        default=False,
        description=(
            "Generate AI documentation for returned table descriptions. "
            "Set true when the user asks for AI analysis, AI documentation, "
            "business documentation, or an AI-generated explanation."
        ),
    )
    save_metadata: bool = Field(
        default=True,
        description="Persist schema and AI documentation metadata when describing tables.",
    )
