from __future__ import annotations

import logging
import sys

from database_bootstrap.bootstrap.errors import SyncInProgressError, UnsafeSnapshotError
from database_bootstrap.bootstrap.runner import SnapshotLoader, run
from database_bootstrap.clients.neo4j import create_driver, wait_until_available
from database_bootstrap.clients.postgres import snapshot_connection
from database_bootstrap.config.settings import Settings, SettingsError
from database_bootstrap.sync.extract import Heartbeat, load_snapshot

logger = logging.getLogger("database_bootstrap")

EXIT_FAILURE = 1
EXIT_SYNC_IN_PROGRESS = 2
EXIT_UNSAFE_SNAPSHOT = 3
EXIT_CONFIGURATION = 64


def _snapshot_loader(settings: Settings) -> SnapshotLoader:
    def load(heartbeat: Heartbeat):
        with snapshot_connection(settings) as connection:
            return load_snapshot(connection, heartbeat)

    return load


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

    try:
        settings = Settings.from_env()
    except SettingsError as error:
        logger.error("%s", error)
        return EXIT_CONFIGURATION

    driver = create_driver(settings)
    try:
        wait_until_available(driver, settings.neo4j_wait_seconds)
        summary = run(settings, driver, _snapshot_loader(settings))
    except SyncInProgressError as error:
        logger.error("%s", error)
        return EXIT_SYNC_IN_PROGRESS
    except UnsafeSnapshotError as error:
        logger.error("%s", error)
        return EXIT_UNSAFE_SNAPSHOT
    except Exception:
        logger.exception("Falha no bootstrap do grafo")
        return EXIT_FAILURE
    finally:
        driver.close()

    logger.info(
        "Snapshot %s ativado: nós=%s relações=%s",
        summary.sync_version,
        summary.nodes,
        summary.relationships,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
