from __future__ import annotations

import logging
import time

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from database_bootstrap.config.settings import Settings

logger = logging.getLogger(__name__)


def create_driver(settings: Settings) -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=10,
        max_connection_pool_size=5,
    )


def wait_until_available(driver: Driver, timeout_seconds: int, interval_seconds: float = 5.0) -> None:
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
