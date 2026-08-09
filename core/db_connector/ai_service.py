from datetime import datetime, timezone
import json
import os
from typing import Dict, Any, Optional
from loguru import logger


class AIDocumentationService:
    """Service to generate basic AI documentation for database table schemas using LiteLLM."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("LITELLM_MODEL", "gpt-4o-mini")

    def generate_table_documentation(
        self, table_description: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generates AI documentation for a table description payload using LiteLLM.

        This method is non-blocking: if LiteLLM is not installed, if API keys are missing,
        or if any API/network error occurs, it catches the exception, logs a warning,
        and returns None without throwing an exception.
        """
        table_name = table_description.get("name", "unknown")
        columns = table_description.get("columns", [])

        prompt = (
            f"Analyse the following database table schema and generate a concise business documentation.\n"
            f"Table Name: {table_name}\n"
            f"Columns: {json.dumps(columns, default=str)}\n"
            f"Primary Key: {table_description.get('primary_key', [])}\n"
            f"Foreign Keys: {json.dumps(table_description.get('foreign_keys', []), default=str)}\n\n"
            f"Return a valid JSON object with the following keys:\n"
            f"- 'summary': A high-level sentence describing the purpose of the table.\n"
            f"- 'column_descriptions': A map of column_name -> brief functional description.\n"
        )

        try:
            import litellm
        except ImportError:
            logger.warning(
                "AIDocumentationService: litellm package is not installed. Skipping AI doc generation."
            )
            return None

        try:
            logger.info(
                f"AIDocumentationService: Generating AI docs for table '{table_name}' using model '{self.model_name}'"
            )

            response = litellm.completion(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Data Architect. Produce clean, structured schema documentation in valid JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            parsed_doc = json.loads(content) if isinstance(content, str) else content

            return {
                "summary": parsed_doc.get("summary", ""),
                "column_descriptions": parsed_doc.get("column_descriptions", {}),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": self.model_name,
            }
        except Exception as e:
            logger.warning(
                f"AIDocumentationService: Failed or skipped AI doc generation for table '{table_name}': {e}"
            )
            return None
