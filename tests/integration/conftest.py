import os
from pathlib import Path

import psycopg
import pytest

from database_bootstrap.clients.neo4j import create_driver
from database_bootstrap.config.settings import Settings, SettingsError

SEED = Path(__file__).parent / "fixtures" / "seed.sql"


@pytest.fixture(scope="session")
def settings() -> Settings:
    if os.environ.get("BOOTSTRAP_TEST_ALLOW_DESTRUCTIVE") != "true":
        pytest.skip("defina BOOTSTRAP_TEST_ALLOW_DESTRUCTIVE=true para rodar contra bancos descartáveis")
    try:
        return Settings.from_env()
    except SettingsError as error:
        pytest.skip(str(error))


@pytest.fixture(scope="session")
def driver(settings):
    instance = create_driver(settings)
    instance.verify_connectivity()
    yield instance
    instance.close()


@pytest.fixture()
def seeded_postgres(settings):
    with psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password,
        sslmode=settings.postgres_sslmode,
        autocommit=True,
    ) as connection:
        connection.execute(SEED.read_text(encoding="utf-8"))
    return settings


@pytest.fixture()
def empty_graph(driver, settings):
    with driver.session(database=settings.neo4j_database) as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    return driver
