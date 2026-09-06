import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger

from .markdown import render_markdown
from .models import ExportFormat, ExportOptions
from .okf import render_okf
from .preformatters import essential_record


class FileArtifactStore:
    """Writes derived exports separately from canonical metadata."""

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)

    @staticmethod
    def _sanitize(name: str) -> str:
        return re.sub(r"[^\w.\-]", "_", name)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.chmod(0o644)
        os.replace(temporary_path, path)

    def _relative_concept_path(self, record: Dict[str, Any]) -> Path:
        return Path(
            self._sanitize(record["config_name"]),
            self._sanitize(record["instance_name"]),
            self._sanitize(record["schema_name"]),
            f"{self._sanitize(record['table_name'])}.md",
        )

    def _write_okf_index(self, bundle_dir: Path) -> None:
        entries = []
        for path in sorted(bundle_dir.rglob("*.md")):
            if path.name in {"index.md", "log.md"}:
                continue
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---\n"):
                continue
            _, frontmatter_text, _ = content.split("---", 2)
            frontmatter = yaml.safe_load(frontmatter_text) or {}
            title = frontmatter.get("title") or path.stem
            description = frontmatter.get("description")
            relative = path.relative_to(bundle_dir).as_posix()
            suffix = f" - {description}" if description else ""
            entries.append(f"* [{title}]({relative}){suffix}")

        body = "\n".join(entries) if entries else "No concepts exported."
        index = f'---\nokf_version: "0.2"\n---\n\n# Database Catalog\n\n{body}\n'
        self._atomic_write(bundle_dir / "index.md", index)

    def export(self, record: Dict[str, Any], options: ExportOptions) -> None:
        export_record = essential_record(record) if options.preformat else record
        relative_path = self._relative_concept_path(record)

        if options.includes(ExportFormat.MARKDOWN):
            path = self.base_dir / ExportFormat.MARKDOWN.value / relative_path
            self._atomic_write(path, render_markdown(export_record))
            logger.info("FileArtifactStore: Saved Markdown export -> {}", path)

        if options.includes(ExportFormat.OKF):
            bundle_dir = self.base_dir / ExportFormat.OKF.value / "catalog"
            path = bundle_dir / relative_path
            self._atomic_write(path, render_okf(export_record))
            self._write_okf_index(bundle_dir)
            logger.info("FileArtifactStore: Saved OKF export -> {}", path)
