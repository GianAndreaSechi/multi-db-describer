from enum import Enum

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    OKF = "okf"


class ExportOptions(BaseModel):
    """Controls derived artifacts without changing the canonical JSON metadata."""

    formats: list[ExportFormat] = Field(
        default_factory=lambda: [ExportFormat.MARKDOWN, ExportFormat.OKF]
    )
    preformat: bool = True

    def includes(self, export_format: ExportFormat) -> bool:
        return export_format in self.formats
