from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

import psycopg

from database_bootstrap import queries
from database_bootstrap.sync.domains import DATASETS, Stage

Heartbeat = Callable[[], None]

_PANEL_POSITIVE_FIELDS = ("power_wp", "dimension", "weight")


@dataclass(frozen=True)
class GraphSnapshot:
    datasets: dict[str, list[dict]]

    def rows(self, dataset: str) -> list[dict]:
        return self.datasets.get(dataset, [])

    def expected_counts(self, stages: Iterable[Stage]) -> dict[str, int]:
        return {
            stage.name: len({tuple(row[field] for field in stage.key) for row in self.rows(stage.dataset)})
            for stage in stages
        }

    @property
    def total_rows(self) -> int:
        return sum(len(rows) for rows in self.datasets.values())


def load_snapshot(connection: psycopg.Connection, heartbeat: Heartbeat | None = None) -> GraphSnapshot:
    datasets: dict[str, list[dict]] = {}
    for name in DATASETS:
        with connection.cursor() as cursor:
            cursor.execute(queries.sql(name))
            rows = [_clean(row) for row in cursor.fetchall()]
        datasets[name] = _filter(name, rows)
        if heartbeat is not None:
            heartbeat()
    return GraphSnapshot(datasets)


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _clean_value(value) for key, value in row.items()}


def _clean_value(value: Any) -> Any:
    if isinstance(value, float) and not isfinite(value):
        return None
    return value


def _filter(dataset: str, rows: Sequence[dict]) -> list[dict]:
    if dataset == "panel_offers":
        return [row for row in rows if _valid_panel_offer(row)]
    return list(rows)


def _valid_panel_offer(row: dict) -> bool:
    if any(row[field] is None or row[field] <= 0 for field in _PANEL_POSITIVE_FIELDS):
        return False
    efficiency = row["efficiency"]
    return efficiency is not None and 0 <= efficiency <= 100
