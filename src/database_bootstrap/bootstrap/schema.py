from __future__ import annotations

from neo4j import Session

from database_bootstrap import queries


def ensure_schema(session: Session) -> None:
    for group in ("constraints", "indexes"):
        for statement in queries.cypher_statements("schema", group):
            session.run(statement).consume()
