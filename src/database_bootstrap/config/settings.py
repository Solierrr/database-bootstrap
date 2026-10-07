from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_database: str
    postgres_user: str
    postgres_password: str
    postgres_sslmode: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    batch_size: int = 500
    lock_lease_seconds: int = 900
    min_domain_retention_ratio: float = 0.5
    neo4j_wait_seconds: int = 300

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        required = (
            "DB_POSTGRES_HOST",
            "DB_POSTGRES_CORE",
            "DB_POSTGRES_USER",
            "DB_POSTGRES_PASSWORD",
            "DB_NEO4J_URI",
            "DB_NEO4J_USER",
            "DB_NEO4J_PASSWORD",
            "DB_NEO4J_FEED",
        )
        missing = [name for name in required if not source.get(name)]
        if missing:
            raise SettingsError("Variáveis de ambiente ausentes: " + ", ".join(missing))

        ratio = _number(source, "SYNC_MIN_DOMAIN_RETENTION_RATIO", 0.5, float)
        if not 0 <= ratio <= 1:
            raise SettingsError("SYNC_MIN_DOMAIN_RETENTION_RATIO deve estar entre 0 e 1")

        batch_size = _number(source, "SYNC_BATCH_SIZE", 500, int)
        lease = _number(source, "SYNC_LOCK_LEASE_SECONDS", 900, int)
        if batch_size < 1 or lease < 1:
            raise SettingsError("SYNC_BATCH_SIZE e SYNC_LOCK_LEASE_SECONDS devem ser positivos")

        return cls(
            postgres_host=source["DB_POSTGRES_HOST"],
            postgres_port=_number(source, "DB_POSTGRES_PORT", 5432, int),
            postgres_database=source["DB_POSTGRES_CORE"],
            postgres_user=source["DB_POSTGRES_USER"],
            postgres_password=source["DB_POSTGRES_PASSWORD"],
            postgres_sslmode=source.get("DB_POSTGRES_SSLMODE") or "require",
            neo4j_uri=source["DB_NEO4J_URI"],
            neo4j_user=source["DB_NEO4J_USER"],
            neo4j_password=source["DB_NEO4J_PASSWORD"],
            neo4j_database=source["DB_NEO4J_FEED"],
            batch_size=batch_size,
            lock_lease_seconds=lease,
            min_domain_retention_ratio=ratio,
            neo4j_wait_seconds=_number(source, "NEO4J_WAIT_SECONDS", 300, int),
        )


def _number(source: Mapping[str, str], name: str, default, cast):
    raw = source.get(name)
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except ValueError as error:
        raise SettingsError(f"{name} inválido: {raw!r}") from error
