from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import IsolationLevel
from psycopg.rows import dict_row

from database_bootstrap.config.settings import Settings


@contextmanager
def snapshot_connection(settings: Settings) -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password,
        sslmode=settings.postgres_sslmode,
        connect_timeout=15,
        row_factory=dict_row,
        autocommit=False,
    )
    try:
        connection.isolation_level = IsolationLevel.REPEATABLE_READ
        connection.read_only = True
        yield connection
    finally:
        connection.rollback()
        connection.close()
