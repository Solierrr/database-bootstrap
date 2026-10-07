from __future__ import annotations

from collections.abc import Iterator

from neo4j import Session

from database_bootstrap import queries
from database_bootstrap.bootstrap import state
from database_bootstrap.config.settings import Settings
from database_bootstrap.sync.domains import NODE_STAGES
from database_bootstrap.sync.extract import GraphSnapshot


def chunks(rows: list[dict], size: int) -> Iterator[list[dict]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def stage_nodes(session: Session, snapshot: GraphSnapshot, sync_version: str, settings: Settings) -> None:
    for stage in NODE_STAGES:
        query = queries.cypher("nodes", stage.query)
        for batch in chunks(snapshot.rows(stage.dataset), settings.batch_size):
            session.run(query, source=state.SOURCE, sync_version=sync_version, rows=batch).consume()
            state.renew_lock(session, sync_version, settings.lock_lease_seconds)
