from __future__ import annotations

from neo4j import Session

from database_bootstrap import queries
from database_bootstrap.bootstrap import state
from database_bootstrap.bootstrap.nodes import chunks
from database_bootstrap.config.settings import Settings
from database_bootstrap.sync.domains import RELATIONSHIP_STAGES
from database_bootstrap.sync.extract import GraphSnapshot


def stage_relationships(
    session: Session, snapshot: GraphSnapshot, sync_version: str, settings: Settings
) -> None:
    for stage in RELATIONSHIP_STAGES:
        query = queries.cypher("relationships", stage.query)
        for batch in chunks(snapshot.rows(stage.dataset), settings.batch_size):
            session.run(query, source=state.SOURCE, sync_version=sync_version, rows=batch).consume()
            state.renew_lock(session, sync_version, settings.lock_lease_seconds)
