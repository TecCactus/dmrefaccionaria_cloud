import os
from dotenv import load_dotenv
from upstash_redis import Redis

# Carga las variables del archivo .env en memoria
load_dotenv()

def get_redis_client() -> Redis:
    """
    Inicializa y retorna el cliente oficial de Upstash Redis usando
    credenciales cargadas desde variables de entorno.
    """
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    if not url or not token:
        raise RuntimeError(
            "Faltan credenciales en el archivo .env (UPSTASH_REDIS_REST_URL o UPSTASH_REDIS_REST_TOKEN)."
        )

    client = Redis.from_env()
    client.ping()
    return client