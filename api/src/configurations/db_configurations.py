import os
from dotenv import load_dotenv
from loguru import logger

# Carica le variabili dal file .env se presente
load_dotenv()

def get_db_configurations():
    """
    Ritorna le configurazioni dei database utilizzando variabili d'ambiente.
    Vengono forniti valori di default per lo sviluppo locale.
    """
    configs = {
        "mysql_dev": {
            "connector_type": "mysql",
            "connection_params": {
                "host": os.getenv("MYSQL_HOST", "host.docker.internal"),
                "user": os.getenv("MYSQL_USER", "root"),
                "password": os.getenv("MYSQL_PASSWORD", ""),
                "port": int(os.getenv("MYSQL_PORT", 3306))
            }
        },
        "sqlite_local": {
            "connector_type": "sqlite",
            "connection_params": {
                "database": os.getenv("SQLITE_DB_PATH", "/app/data/test.db")
            }
        },
        "duckdb_local": {
            "connector_type": "duckdb",
            "connection_params": {
                "database": os.getenv("DUCKDB_PATH", "/app/data/duck.db")
            }
        }
    }
    
    logger.info(f"Loaded {len(configs)} database configurations from environment/defaults.")
    return configs

# Esponiamo direttamente il dizionario per semplicità di importazione
DB_CONFIGURATIONS = get_db_configurations()
