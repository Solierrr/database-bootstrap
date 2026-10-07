import pytest

import main
from main import BootstrapError, Settings

BASE_ENV = {
    "DB_POSTGRES_HOST": "db.example.com",
    "DB_POSTGRES_CORE": "coredb",
    "DB_POSTGRES_USER": "reader",
    "DB_POSTGRES_PASSWORD": "secret",
    "DB_NEO4J_URI": "bolt://feeddb:7687",
    "DB_NEO4J_USER": "neo4j",
    "DB_NEO4J_PASSWORD": "graph-secret",
    "DB_NEO4J_FEED": "feeddb",
}


def test_from_env_reads_required_values_and_applies_defaults():
    settings = Settings.from_env(BASE_ENV)

    assert settings.postgres == {
        "host": "db.example.com",
        "port": 5432,
        "dbname": "coredb",
        "user": "reader",
        "password": "secret",
        "sslmode": "require",
    }
    assert settings.neo4j_uri == "bolt://feeddb:7687"
    assert settings.neo4j_database == "feeddb"
    assert settings.batch_size == 500
    assert settings.lock_lease_seconds == 900
    assert settings.minimum_ratio == 0.5
    assert settings.neo4j_wait_seconds == 300


def test_from_env_reports_every_missing_variable():
    env = {key: value for key, value in BASE_ENV.items() if key not in {"DB_NEO4J_FEED", "DB_POSTGRES_HOST"}}

    with pytest.raises(BootstrapError) as error:
        Settings.from_env(env)

    assert "DB_NEO4J_FEED" in str(error.value)
    assert "DB_POSTGRES_HOST" in str(error.value)


def test_from_env_accepts_overrides():
    env = {
        **BASE_ENV,
        "DB_POSTGRES_PORT": "6543",
        "DB_POSTGRES_SSLMODE": "verify-full",
        "SYNC_BATCH_SIZE": "50",
        "SYNC_LOCK_LEASE_SECONDS": "120",
        "SYNC_MIN_DOMAIN_RETENTION_RATIO": "0.8",
        "NEO4J_WAIT_SECONDS": "30",
    }

    settings = Settings.from_env(env)

    assert settings.postgres["port"] == 6543
    assert settings.postgres["sslmode"] == "verify-full"
    assert settings.batch_size == 50
    assert settings.lock_lease_seconds == 120
    assert settings.minimum_ratio == 0.8
    assert settings.neo4j_wait_seconds == 30


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SYNC_MIN_DOMAIN_RETENTION_RATIO", "1.5"),
        ("SYNC_MIN_DOMAIN_RETENTION_RATIO", "abc"),
        ("SYNC_BATCH_SIZE", "0"),
        ("SYNC_BATCH_SIZE", "many"),
        ("SYNC_LOCK_LEASE_SECONDS", "-1"),
        ("DB_POSTGRES_PORT", "port"),
    ],
)
def test_from_env_rejects_invalid_numbers(name, value):
    with pytest.raises(BootstrapError):
        Settings.from_env({**BASE_ENV, name: value})


def test_main_exits_with_configuration_code_when_env_is_missing(monkeypatch):
    for name in main.CONFIG["required_env"]:
        monkeypatch.delenv(name, raising=False)

    assert main.main() == main.Exit.CONFIGURATION


def test_main_returns_the_exit_code_carried_by_the_error(monkeypatch):
    def refuse():
        raise BootstrapError("recusado", main.Exit.UNSAFE_SNAPSHOT)

    monkeypatch.setattr(main.Settings, "from_env", refuse)

    assert main.main() == main.Exit.UNSAFE_SNAPSHOT
