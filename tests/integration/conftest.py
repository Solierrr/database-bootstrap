import os
from pathlib import Path

import psycopg
import pytest
from neo4j import GraphDatabase

from main import BootstrapError, Settings

SEED = Path(__file__).parent / "fixtures" / "seed.sql"


@pytest.fixture(scope="session")
def settings() -> Settings:
    if os.environ.get("BOOTSTRAP_TEST_ALLOW_DESTRUCTIVE") != "true":
        pytest.skip("defina BOOTSTRAP_TEST_ALLOW_DESTRUCTIVE=true para rodar contra bancos descartáveis")
    try:
        return Settings.from_env()
    except BootstrapError as error:
        pytest.skip(str(error))


@pytest.fixture(scope="session")
def driver(settings):
    instance = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    instance.verify_connectivity()
    yield instance
    instance.close()


@pytest.fixture()
def seeded_postgres(settings):
    with psycopg.connect(**settings.postgres, autocommit=True) as connection:
        connection.execute(SEED.read_text(encoding="utf-8"))
    return settings


@pytest.fixture()
def empty_graph(driver, settings):
    with driver.session(database=settings.neo4j_database) as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    return driver
