from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable
from psycopg import IsolationLevel
from psycopg.rows import dict_row

SRC = Path(__file__).parent
CONFIG: dict[str, Any] = json.loads((SRC / "config.json").read_text(encoding="utf-8"))
SOURCE: str = CONFIG["source"]

logger = logging.getLogger("database_bootstrap")

_SECTION = re.compile(r"^--\s*(dataset|fragment):\s*(\w+)\s*$", re.MULTILINE)
_INCLUDE = re.compile(r"^--\s*include:\s*(\w+)\s*$", re.MULTILINE)
_DATASET = re.compile(r"\A//\s*dataset:\s*(\w+)")

Rows = dict[str, list[dict]]
Heartbeat = Callable[[], None]


class Exit(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    SYNC_IN_PROGRESS = 2
    UNSAFE_SNAPSHOT = 3
    CONFIGURATION = 64


class BootstrapError(RuntimeError):
    exit_code = Exit.FAILURE


class SettingsError(BootstrapError):
    exit_code = Exit.CONFIGURATION


class SyncInProgressError(BootstrapError):
    exit_code = Exit.SYNC_IN_PROGRESS


class UnsafeSnapshotError(BootstrapError):
    exit_code = Exit.UNSAFE_SNAPSHOT


@dataclass(frozen=True)
class Settings:
    postgres: dict
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    batch_size: int
    lock_lease_seconds: int
    minimum_ratio: float
    neo4j_wait_seconds: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        missing = [name for name in CONFIG["required_env"] if not source.get(name)]
        if missing:
            raise SettingsError("Variáveis de ambiente ausentes: " + ", ".join(missing))

        def number(key: str) -> Any:
            spec = CONFIG["numbers"][key]
            raw = source.get(spec["env"]) or spec["default"]
            try:
                value = type(spec["default"])(raw)
            except ValueError as error:
                raise SettingsError(f"{spec['env']} inválido: {raw!r}") from error
            low, high = spec.get("min", 0), spec.get("max")
            if value < low or (high is not None and value > high):
                raise SettingsError(f"{spec['env']} deve estar entre {low} e {'∞' if high is None else high}")
            return value

        return cls(
            postgres={
                "host": source["DB_POSTGRES_HOST"],
                "port": number("port"),
                "dbname": source["DB_POSTGRES_CORE"],
                "user": source["DB_POSTGRES_USER"],
                "password": source["DB_POSTGRES_PASSWORD"],
                "sslmode": source.get("DB_POSTGRES_SSLMODE") or CONFIG["postgres"]["sslmode"],
            },
            neo4j_uri=source["DB_NEO4J_URI"],
            neo4j_user=source["DB_NEO4J_USER"],
            neo4j_password=source["DB_NEO4J_PASSWORD"],
            neo4j_database=source["DB_NEO4J_FEED"],
            batch_size=number("batch_size"),
            lock_lease_seconds=number("lock_lease_seconds"),
            minimum_ratio=number("minimum_ratio"),
            neo4j_wait_seconds=number("neo4j_wait_seconds"),
        )


@dataclass(frozen=True)
class Stage:
    name: str
    dataset: str
    query: str


def queries() -> dict[str, str]:
    parts = _SECTION.split((SRC / "extract.sql").read_text(encoding="utf-8"))
    fragments: dict[str, str] = {}
    datasets: dict[str, str] = {}
    for kind, name, body in zip(parts[1::3], parts[2::3], parts[3::3], strict=True):
        (fragments if kind == "fragment" else datasets)[name] = body.strip()
    return {
        name: _INCLUDE.sub(lambda match: fragments[match.group(1)], body) for name, body in datasets.items()
    }


def cypher(name: str) -> str:
    return (SRC / "graphs" / f"{name}.cypher").read_text(encoding="utf-8")


def stages() -> list[Stage]:
    found = []
    for group in ("nodes", "relationships"):
        for path in sorted((SRC / "graphs" / group).glob("*.cypher")):
            query = path.read_text(encoding="utf-8")
            header = _DATASET.match(query)
            if header is None:
                raise ValueError(f"{path.name} precisa começar com '// dataset: <nome>'")
            found.append(Stage(f"{group}/{path.stem}", header.group(1), query))
    return found


def chunks(rows: list[dict], size: int) -> Iterator[list[dict]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def extract(connection: psycopg.Connection, heartbeat: Heartbeat | None = None) -> Rows:
    rows: Rows = {}
    for dataset, query in queries().items():
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows[dataset] = cursor.fetchall()
        if heartbeat is not None:
            heartbeat()
    return rows


def postgres_loader(settings: Settings) -> Callable[[Heartbeat], Rows]:
    def load(heartbeat: Heartbeat) -> Rows:
        with psycopg.connect(
            **settings.postgres, connect_timeout=CONFIG["postgres"]["connect_timeout"], row_factory=dict_row
        ) as connection:
            connection.isolation_level = IsolationLevel.REPEATABLE_READ
            connection.read_only = True
            return extract(connection, heartbeat)

    return load


def _run(session: Session, name: str, **parameters):
    return session.run(cypher(f"snapshot/{name}"), source=SOURCE, **parameters)


def _begin(session: Session, version: str, lease: int) -> str | None:
    record = _run(session, "acquire_lock", sync_version=version, lease_seconds=lease).single()
    if record is None:
        raise SyncInProgressError("Já existe uma sincronização em andamento.")
    try:
        orphans = _run(session, "register_unreferenced_versions", sync_version=version).single()
        _cleanup(session, version, list(orphans["cleanup_versions"] or []) if orphans else [])
    except Exception:
        logger.exception("Falha ao recuperar versões órfãs; elas permanecerão pendentes")
    return record["active_version"]


def _renew(session: Session, version: str, lease: int) -> None:
    if _run(session, "renew_lock", sync_version=version, lease_seconds=lease).single() is None:
        raise UnsafeSnapshotError("O lock da sincronização foi perdido antes da ativação.")


def _cleanup(session: Session, version: str, versions: list[str]) -> None:
    unique = sorted({item for item in versions if item})
    if unique:
        _run(session, "delete_snapshot_versions", sync_version=version, cleanup_versions=unique).consume()
        _run(session, "clear_cleanup_versions", sync_version=version, cleanup_versions=unique).consume()


def _abort(session: Session, version: str) -> None:
    try:
        registered = _run(session, "register_cleanup_version", sync_version=version, cleanup_version=version)
        if registered.single() is not None:
            _cleanup(session, version, [version])
    except Exception:
        logger.exception("Falha ao descartar o staging da sincronização %s", version)
    try:
        _run(session, "release_lock", sync_version=version).consume()
    except Exception:
        logger.exception("Falha ao liberar o lock da sincronização %s", version)


def _stage(session: Session, rows: Rows, version: str, settings: Settings) -> dict[str, int]:
    counts: dict[str, int] = {}
    for stage in stages():
        staged = rows.get(stage.dataset, [])
        merged = 0
        for batch in chunks(staged, settings.batch_size):
            result = session.run(stage.query, source=SOURCE, sync_version=version, rows=batch).single()
            merged += result["merged"]
            _renew(session, version, settings.lock_lease_seconds)
        if merged != len(staged):
            raise UnsafeSnapshotError(f"{stage.name}: {len(staged)} linhas lidas, {merged} gravadas")
        counts[stage.name] = merged
    return counts


def _activate(session: Session, version: str) -> list[str]:
    failure: Exception | None = None
    record = None
    try:
        record = _run(session, "activate_snapshot", sync_version=version).single()
    except Exception as error:
        failure = error
    if record is None:
        record = _run(session, "reconcile_activation", sync_version=version).single()
    if record is None:
        raise failure or UnsafeSnapshotError("O lock da sincronização foi perdido antes da ativação.")
    return list(record["cleanup_versions"] or [])


def run(settings: Settings, driver: Driver, load: Callable[[Heartbeat], Rows]) -> tuple[str, dict[str, int]]:
    version = str(uuid4())
    lease = settings.lock_lease_seconds

    with driver.session(database=settings.neo4j_database) as session:
        for statement in cypher("schema").split(";"):
            if statement.strip():
                session.run(statement).consume()

        active = _begin(session, version, lease)
        activated = False
        try:
            rows = load(lambda: _renew(session, version, lease))
            counts = _stage(session, rows, version, settings)

            violations = _run(
                session,
                "validate",
                sync_version=version,
                active_version=active,
                minimum_ratio=settings.minimum_ratio,
            ).data()
            if violations:
                drops = "; ".join(f"{v['name']}: {v['staged']}/{v['active']}" for v in violations)
                raise UnsafeSnapshotError("Snapshot recusado por queda anormal de domínio: " + drops)

            _renew(session, version, lease)
            pending = _activate(session, version)
            activated = True
            try:
                _cleanup(session, version, pending)
            except Exception:
                logger.exception("Snapshot ativado, mas a limpeza das versões %s falhou", pending)
        finally:
            if activated:
                try:
                    _run(session, "release_lock", sync_version=version).consume()
                except Exception:
                    logger.exception("Snapshot %s ativado, mas o lock não foi liberado", version)
            else:
                _abort(session, version)

    return version, counts


def wait_until_available(
    driver: Driver, timeout_seconds: int, interval_seconds: float = CONFIG["neo4j"]["retry_interval"]
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            driver.verify_connectivity()
            return
        except (ServiceUnavailable, OSError) as error:
            if time.monotonic() >= deadline:
                raise
            logger.info("Neo4j ainda indisponível (%s); nova tentativa em %.0fs", error, interval_seconds)
            time.sleep(interval_seconds)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

    try:
        settings = Settings.from_env()
        with GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=CONFIG["neo4j"]["connection_timeout"],
            max_connection_pool_size=CONFIG["neo4j"]["max_pool_size"],
        ) as driver:
            wait_until_available(driver, settings.neo4j_wait_seconds)
            version, counts = run(settings, driver, postgres_loader(settings))
    except BootstrapError as error:
        logger.error("%s", error)
        return error.exit_code
    except Exception:
        logger.exception("Falha no bootstrap do grafo")
        return Exit.FAILURE

    logger.info("Snapshot %s ativado: %s", version, counts)
    return Exit.SUCCESS


if __name__ == "__main__":
    sys.exit(main())
