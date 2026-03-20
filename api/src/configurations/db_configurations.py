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
                "hosts": [
                    {
                        "host": os.getenv("MYSQL_HOST_1", "host.docker.internal"),
                        "user": os.getenv("MYSQL_USER_1", "root"),
                        "password": os.getenv("MYSQL_PASSWORD_1", ""),
                        "port": int(os.getenv("MYSQL_PORT_1", 3306))
                    },
                    {
                        "host": os.getenv("MYSQL_HOST_2", "host.docker.internal"),
                        "user": os.getenv("MYSQL_USER_2", "root"),
                        "password": os.getenv("MYSQL_PASSWORD_2", ""),
                        "port": int(os.getenv("MYSQL_PORT_2", 3306))
                    }
                ]
            }
        }
    }
    
    logger.info(f"Loaded {len(configs)} database configurations from environment/defaults.")
    return configs

# Esponiamo direttamente il dizionario per semplicità di importazione
DB_CONFIGURATIONS = get_db_configurations()
