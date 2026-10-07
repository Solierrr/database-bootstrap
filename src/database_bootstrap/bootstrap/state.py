from __future__ import annotations

import logging
from collections.abc import Iterable

from neo4j import Session

from database_bootstrap import queries
from database_bootstrap.bootstrap.errors import SyncInProgressError, UnsafeSnapshotError

logger = logging.getLogger(__name__)

SOURCE = "api-core"


def _run(session: Session, name: str, **parameters):
    return session.run(queries.cypher("snapshot", name), source=SOURCE, **parameters)


def begin_sync(session: Session, sync_version: str, lease_seconds: int) -> str | None:
    record = _run(session, "acquire_lock", sync_version=sync_version, lease_seconds=lease_seconds).single()
    if record is None:
        raise SyncInProgressError("Já existe uma sincronização em andamento.")

    try:
        cleanup = _run(session, "register_unreferenced_versions", sync_version=sync_version).single()
        versions = list(cleanup["cleanup_versions"] or []) if cleanup else []
        cleanup_versions(session, sync_version, versions)
    except Exception:
        logger.exception("Falha ao recuperar versões órfãs; elas permanecerão pendentes")

    return record["active_version"]


def renew_lock(session: Session, sync_version: str, lease_seconds: int) -> None:
    record = _run(session, "renew_lock", sync_version=sync_version, lease_seconds=lease_seconds).single()
    if record is None:
        raise UnsafeSnapshotError("O lock da sincronização foi perdido antes da ativação.")


def release_lock(session: Session, sync_version: str) -> None:
    _run(session, "release_lock", sync_version=sync_version).consume()


def cleanup_versions(session: Session, sync_version: str, versions: Iterable[str]) -> None:
    unique = sorted({version for version in versions if version})
    if not unique:
        return
    _run(session, "delete_snapshot_versions", sync_version=sync_version, cleanup_versions=unique).consume()
    _run(session, "clear_cleanup_versions", sync_version=sync_version, cleanup_versions=unique).consume()


def abort_sync(session: Session, sync_version: str) -> None:
    try:
        registered = (
            _run(
                session,
                "register_cleanup_version",
                sync_version=sync_version,
                cleanup_version=sync_version,
            ).single()
            is not None
        )
        if registered:
            cleanup_versions(session, sync_version, [sync_version])
    except Exception:
        logger.exception("Falha ao registrar ou descartar o staging da sincronização %s", sync_version)
    try:
        release_lock(session, sync_version)
    except Exception:
        logger.exception("Falha ao liberar o lock da sincronização %s", sync_version)


def snapshot_counts(session: Session, sync_version: str) -> tuple[dict[str, int], dict[str, int]]:
    nodes = {
        record["name"]: int(record["total"])
        for record in _run(session, "node_counts", sync_version=sync_version)
    }
    relationships = {
        record["name"]: int(record["total"])
        for record in _run(session, "relationship_counts", sync_version=sync_version)
    }
    return nodes, relationships


def activate(session: Session, sync_version: str) -> list[str]:
    failure: Exception | None = None
    record = None
    try:
        record = _run(session, "activate_snapshot", sync_version=sync_version).single()
    except Exception as error:
        failure = error

    if record is None:
        record = _run(session, "reconcile_activation", sync_version=sync_version).single()

    if record is None:
        if failure is not None:
            raise failure
        raise UnsafeSnapshotError("O lock da sincronização foi perdido antes da ativação.")

    return list(record["cleanup_versions"] or [])
