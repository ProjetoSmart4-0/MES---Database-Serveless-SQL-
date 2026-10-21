import os
import psycopg2
from psycopg2.extras import RealDictCursor

# A URL do Neon Postgres deve ser configurada no arquivo .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_ya6PT8pOwVdR@ep-small-math-b63iws54-pooler.c-2.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db_connection():
    """Abre uma conexão segura com o Neon Postgres."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn