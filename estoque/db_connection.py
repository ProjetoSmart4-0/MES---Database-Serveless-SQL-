
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Localiza o .env na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


def get_db_connection():
    """Abre uma conexão com o Neon PostgreSQL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL não configurada. "
            "Verifique o arquivo .env na raiz do projeto."
        )

    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor,
        connect_timeout=10
    )
