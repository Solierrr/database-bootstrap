from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from neo4j import Driver, Session

from database_bootstrap.bootstrap import schema, state
from database_bootstrap.bootstrap.errors import UnsafeSnapshotError
from database_bootstrap.bootstrap.nodes import stage_nodes
from database_bootstrap.bootstrap.relationships import stage_relationships
from database_bootstrap.bootstrap.validation import validate_domain_retention, validate_exact_counts
from database_bootstrap.config.settings import Settings
from database_bootstrap.sync.domains import NODE_STAGES, RELATIONSHIP_STAGES
from database_bootstrap.sync.extract import GraphSnapshot, Heartbeat

logger = logging.getLogger(__name__)

SnapshotLoader = Callable[[Heartbeat], GraphSnapshot]


@dataclass(frozen=True)
class SyncSummary:
    sync_version: str
    nodes: dict[str, int]
    relationships: dict[str, int]


def run(settings: Settings, driver: Driver, load_snapshot: SnapshotLoader) -> SyncSummary:
    sync_version = str(uuid4())
    lease = settings.lock_lease_seconds

    with driver.session(database=settings.neo4j_database) as session:
        schema.ensure_schema(session)
        active_version = state.begin_sync(session, sync_version, lease)
        activated = False
        try:
            snapshot = load_snapshot(lambda: state.renew_lock(session, sync_version, lease))
            summary = _stage_and_activate(session, snapshot, sync_version, active_version, settings)
            activated = True
        finally:
            if activated:
                try:
                    state.release_lock(session, sync_version)
                except Exception:
                    logger.exception(
                        "Snapshot %s ativado, mas o lock não pôde ser liberado; a lease expirará sozinha",
                        sync_version,
                    )
            else:
                state.abort_sync(session, sync_version)

    return summary


def _stage_and_activate(
    session: Session,
    snapshot: GraphSnapshot,
    sync_version: str,
    active_version: str | None,
    settings: Settings,
) -> SyncSummary:
    lease = settings.lock_lease_seconds
    expected_nodes = snapshot.expected_counts(NODE_STAGES)
    expected_relationships = snapshot.expected_counts(RELATIONSHIP_STAGES)

    if active_version:
        if sum(expected_nodes.values()) == 0:
            raise UnsafeSnapshotError("Snapshot vazio recusado porque já existe uma versão ativa.")
        active_nodes, active_relationships = state.snapshot_counts(session, active_version)
        validate_domain_retention(active_nodes, expected_nodes, settings.min_domain_retention_ratio)
        validate_domain_retention(
            active_relationships, expected_relationships, settings.min_domain_retention_ratio
        )

    state.renew_lock(session, sync_version, lease)
    stage_nodes(session, snapshot, sync_version, settings)
    stage_relationships(session, snapshot, sync_version, settings)

    actual_nodes, actual_relationships = state.snapshot_counts(session, sync_version)
    validate_exact_counts(expected_nodes, actual_nodes, "nós")
    validate_exact_counts(expected_relationships, actual_relationships, "relações")

    state.renew_lock(session, sync_version, lease)
    pending = state.activate(session, sync_version)
    if pending:
        try:
            state.cleanup_versions(session, sync_version, pending)
        except Exception:
            logger.exception(
                "Snapshot ativado, mas a limpeza das versões %s falhou; elas permanecerão pendentes", pending
            )

    return SyncSummary(sync_version, expected_nodes, expected_relationships)
