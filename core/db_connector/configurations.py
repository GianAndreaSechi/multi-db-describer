import os
from dotenv import load_dotenv
from loguru import logger

# Containers mount each component's configuration in a different directory.
# DB_CONFIG_FILE makes that location explicit while preserving normal local
# dotenv discovery when it is not set.
load_dotenv(dotenv_path=os.getenv("DB_CONFIG_FILE") or None)


def _env(key: str) -> str | None:
    """Returns the env var value only if explicitly set and non-empty, else None."""
    val = os.getenv(key)
    return val if val else None


def get_db_configurations() -> dict:
    """
    Builds the active database configurations from environment variables.

    A configuration is included only if its primary activation env var is set.
    Developers do not need to comment/uncomment entries — just set the relevant
    env vars and the config will be picked up automatically.

    Activation env vars:
      mysql_dev   → MYSQL_DBPUBLISHERS_HOST or MYSQL_DBCATALOGUE_HOST (each host is independent)
      postgres_dev → POSTGRES_HOST
      athena       → ATHENA_REGION
      trino        → TRINO_HOST
      presto       → PRESTO_HOST
      dynamodb     → DYNAMODB_REGION
      mongodb      → MONGODB_HOST
    """
    configs = {}

    # ── MySQL ──────────────────────────────────────────────────────────────────
    # Each host is added independently; the config is enabled if at least one is set.
    mysql_hosts = []
    if _env("MYSQL_DB1_HOST"):
        mysql_hosts.append({
            "host":     _env("MYSQL_DB1_HOST"),
            "user":     os.getenv("MYSQL_DB1_USER", "root"),
            "password": os.getenv("MYSQL_DB1_PASSWORD", ""),
            "port":     int(os.getenv("MYSQL_DB1_PORT", 3306)),
        })
    if _env("MYSQL_DB2_HOST"):
        mysql_hosts.append({
            "host":     _env("MYSQL_DB2_HOST"),
            "user":     os.getenv("MYSQL_DB2_USER", "root"),
            "password": os.getenv("MYSQL_DB2_PASSWORD", ""),
            "port":     int(os.getenv("MYSQL_DB2_PORT", 3306)),
        })
    if mysql_hosts:
        configs["mysql_dev"] = {
            "connector_type": "mysql",
            "connection_params": {"hosts": mysql_hosts},
        }

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    if _env("POSTGRES_HOST"):
        configs["postgres_dev"] = {
            "connector_type": "postgres",
            "connection_params": {
                "host":      _env("POSTGRES_HOST"),
                "port":      int(os.getenv("POSTGRES_PORT", 5432)),
                "user":      os.getenv("POSTGRES_USER", "postgres"),
                "password":  os.getenv("POSTGRES_PASSWORD", ""),
                "database":  os.getenv("POSTGRES_DB", "postgres"),
                "pool_size": int(os.getenv("POSTGRES_POOL_SIZE", 5)),
            },
        }

    # ── Amazon Athena ──────────────────────────────────────────────────────────
    # AWS credentials are optional when running with an IAM role.
    if _env("ATHENA_REGION"):
        configs["athena"] = {
            "connector_type": "athena",
            "connection_params": {
                "catalog":               os.getenv("ATHENA_CATALOG", "AwsDataCatalog"),
                "region":                _env("ATHENA_REGION"),
                "s3_output_location":    os.getenv("ATHENA_S3_OUTPUT", ""),
                "aws_access_key_id":     _env("AWS_ACCESS_KEY_ID"),
                "aws_secret_access_key": _env("AWS_SECRET_ACCESS_KEY"),
                "aws_session_token":     _env("AWS_SESSION_TOKEN"),
            },
        }

    # ── Trino ──────────────────────────────────────────────────────────────────
    if _env("TRINO_HOST"):
        configs["trino"] = {
            "connector_type": "trino",
            "connection_params": {
                "host":               _env("TRINO_HOST"),
                "port":               int(os.getenv("TRINO_PORT", 8080)),
                "user":               os.getenv("TRINO_USER", "trino"),
                "password":           _env("TRINO_PASSWORD"),
                "http_scheme":        os.getenv("TRINO_HTTP_SCHEME", "http"),
                "session_properties": {},
            },
        }

    # ── Presto ─────────────────────────────────────────────────────────────────
    if _env("PRESTO_HOST"):
        configs["presto"] = {
            "connector_type": "presto",
            "connection_params": {
                "host":        _env("PRESTO_HOST"),
                "port":        int(os.getenv("PRESTO_PORT", 8080)),
                "user":        os.getenv("PRESTO_USER", "presto"),
                "password":    _env("PRESTO_PASSWORD"),
                "http_scheme": os.getenv("PRESTO_HTTP_SCHEME", "http"),
            },
        }

    # ── Amazon DynamoDB ────────────────────────────────────────────────────────
    if _env("DYNAMODB_REGION"):
        configs["dynamodb"] = {
            "connector_type": "dynamodb",
            "connection_params": {
                "region":                _env("DYNAMODB_REGION"),
                "aws_access_key_id":     _env("AWS_ACCESS_KEY_ID"),
                "aws_secret_access_key": _env("AWS_SECRET_ACCESS_KEY"),
                "aws_session_token":     _env("AWS_SESSION_TOKEN"),
                "endpoint_url":          _env("DYNAMODB_ENDPOINT_URL"),
            },
        }

    # ── MongoDB ────────────────────────────────────────────────────────────────
    if _env("MONGODB_HOST"):
        configs["mongodb"] = {
            "connector_type": "mongodb",
            "connection_params": {
                "host":       _env("MONGODB_HOST"),
                "port":       int(os.getenv("MONGODB_PORT", 27017)),
                "username":   _env("MONGODB_USER"),
                "password":   _env("MONGODB_PASSWORD"),
                "authSource": os.getenv("MONGODB_AUTH_SOURCE", "admin"),
                "tls":        os.getenv("MONGODB_TLS", "false").lower() == "true",
                "tlsAllowInvalidCertificates": os.getenv("MONGODB_TLS_ALLOW_INVALID", "false").lower() == "true",
            },
        }

    logger.info(f"Active DB configurations: {list(configs.keys()) or 'none'}")
    return configs


DB_CONFIGURATIONS = get_db_configurations()
