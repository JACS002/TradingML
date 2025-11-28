import os
from sqlalchemy import create_engine, text


def get_db_url() -> str:
    """Construye la URL de conexión a Postgres a partir de variables de entorno."""
    host = os.environ.get("PG_HOST", "postgres")
    port = os.environ.get("PG_PORT", "5432")
    db   = os.environ.get("PG_DB", "trading_db")
    user = os.environ.get("PG_USER", "postgres")
    pwd  = os.environ.get("PG_PASSWORD", "postgres")

    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def get_engine():
    """Devuelve un engine de SQLAlchemy para conectarse a Postgres."""
    db_url = get_db_url()
    engine = create_engine(db_url)
    return engine


def ensure_schemas():
    """
    Crea los esquemas raw y analytics si no existen.
    Esto se llama al inicio del feature-builder.
    """
    schema_raw = os.environ.get("PG_SCHEMA_RAW", "raw")
    schema_analytics = os.environ.get("PG_SCHEMA_ANALYTICS", "analytics")

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_raw};"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_analytics};"))
        conn.commit()
