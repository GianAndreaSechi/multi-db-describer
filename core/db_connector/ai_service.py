from datetime import datetime, timezone
import json
import os
import time
from typing import Dict, Any, Optional
from loguru import logger


class AIDocumentationService:
    """Service to generate basic AI documentation for database table schemas using LiteLLM."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("LITELLM_MODEL") or "gpt-4o-mini"
        self.timeout = int(os.getenv("LITELLM_TIMEOUT_SECONDS", "120"))
        self.max_retries = int(os.getenv("LITELLM_MAX_RETRIES", "2"))
        self.last_error: Optional[str] = None

    def generate_table_documentation(
        self, table_description: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generates AI documentation for a table description payload using LiteLLM.

        This method is non-blocking: if LiteLLM is not installed, if API keys are missing,
        or if any API/network error occurs, it catches the exception, logs a warning,
        and returns None without throwing an exception.
        """
        table_name = table_description.get("table_name", "unknown")
        schema_name = table_description.get("schema_name", "unknown")
        instance_name = table_description.get("instance_name", "unknown")
        columns = table_description.get("columns", [])
        self.last_error = None

        prompt = (
            f"Analyse the following database table schema and generate a concise business documentation.\n"
            f"Instance Name: {instance_name}\n"
            f"Schema Name: {schema_name}\n"
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
            self.last_error = "litellm package is not installed"
            logger.warning(f"AIDocumentationService: {self.last_error}. Skipping AI doc generation.")
            return None

        try:
            logger.info(
                f"AIDocumentationService: Generating AI docs for table '{table_name}' using model '{self.model_name}'"
            )

            kwargs = {}
            if os.getenv("LITELLM_API_KEY"):
                kwargs["api_key"] = os.getenv("LITELLM_API_KEY")
            if os.getenv("LITELLM_API_BASE"):
                kwargs["api_base"] = os.getenv("LITELLM_API_BASE")

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Data Architect. Produce clean, structured schema documentation in valid JSON format.",
                },
                {"role": "user", "content": prompt},
            ]

            last_attempt_error: Optional[Exception] = None
            response = None
            for attempt in range(self.max_retries):
                try:
                    response = litellm.completion(
                        model=self.model_name,
                        messages=messages,
                        response_format={"type": "json_object"},
                        timeout=self.timeout,
                        **kwargs,
                    )
                    break
                except Exception as attempt_exc:
                    last_attempt_error = attempt_exc
                    logger.warning(
                        f"AIDocumentationService: attempt {attempt + 1}/{self.max_retries} failed for '{table_name}': {attempt_exc}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(2)

            if response is None:
                raise last_attempt_error


            content = response.choices[0].message.content
            if not content:
                self.last_error = f"Empty response content from model '{self.model_name}'"
                logger.warning(f"AIDocumentationService: {self.last_error} for table '{table_name}'")
                return None

            # Strip markdown code fences if present (e.g. ```json ... ```)
            stripped = content.strip()
            if stripped.startswith("```"):
                stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
                if stripped.endswith("```"):
                    stripped = stripped[:-3].strip()
            else:
                stripped = stripped

            try:
                parsed_doc = json.loads(stripped)
            except json.JSONDecodeError:
                self.last_error = f"Non-JSON response from model '{self.model_name}': {content!r:.200}"
                logger.warning(f"AIDocumentationService: {self.last_error} for table '{table_name}'")
                return None

            logger.info(
                f"AIDocumentationService: AI docs generated for table '{table_name}' using model '{self.model_name}'"
            )

            return {
                "summary": parsed_doc.get("summary", ""),
                "column_descriptions": parsed_doc.get("column_descriptions", {}),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": self.model_name,
            }
        except Exception as e:
            self.last_error = str(e)
            logger.warning(
                f"AIDocumentationService: Failed or skipped AI doc generation for table '{table_name}': {e}"
            )
            return None
