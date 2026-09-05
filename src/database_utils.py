import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy import text

def create_postgis_engine(env_path):
    """
    Create SQLAlchemy engine from .env database settings.
    """

    load_dotenv(env_path)

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    required = {
        "DB_HOST": db_host,
        "DB_PORT": db_port,
        "DB_NAME": db_name,
        "DB_USER": db_user,
        "DB_PASSWORD": db_password
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        raise ValueError(
            f"Missing database environment variables: {missing}"
        )

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True
    )

    return engine


def export_to_postgis(
    gdf,
    engine,
    table_name,
    schema="taipei_landuse",
    if_exists="replace"
):
    """
    Export a GeoDataFrame to PostGIS.
    """

    gdf.to_postgis(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=False
    )




def get_table_count(
    engine,
    schema,
    table_name
):
    """
    Return row count for a PostGIS table.
    """

    query = text(
        f"""
        SELECT COUNT(*)
        FROM {schema}.{table_name};
        """
    )

    with engine.connect() as conn:
        return conn.execute(query).scalar()