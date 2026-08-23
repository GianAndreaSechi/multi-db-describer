from typing import Optional
from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    config_name: Optional[str] = Field(default=None, description="Configured database target name.")
    instance_name: Optional[str] = Field(default=None, description="Database instance returned by list_instances.")
    schema_name: Optional[str] = Field(default=None, description="Schema/database name.")
    generate_ai_docs: bool = Field(
        default=False,
        description=(
            "Generate AI documentation for scanned tables. Set true when the user asks for AI analysis, "
            "AI documentation, business documentation, or an AI-generated explanation."
        ),
    )
    save_metadata: bool = Field(default=True, description="Persist generated metadata.")
    only_if_changed: bool = Field(default=False, description="Skip metadata writes when the schema has not changed.")
    save_markdown: bool = Field(default=False, description="Save an LLM-friendly Markdown document alongside JSON metadata.")
