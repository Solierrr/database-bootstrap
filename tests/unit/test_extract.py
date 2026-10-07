from math import inf, nan

from database_bootstrap.sync.domains import DATASETS, NODE_STAGES, RELATIONSHIP_STAGES
from database_bootstrap.sync.extract import GraphSnapshot, _clean, _valid_panel_offer, load_snapshot


def panel_row(**overrides):
    row = {
        "model_id": "m1",
        "supplier_id": "s1",
        "offer_id": "o1",
        "power_wp": 550.0,
        "efficiency": 21.5,
        "dimension": 2.53,
        "weight": 28.0,
    }
    return {**row, **overrides}


def test_expected_counts_deduplicate_by_stage_key():
    snapshot = GraphSnapshot(
        {
            "panel_offers": [
                panel_row(),
                panel_row(offer_id="o2"),
                panel_row(offer_id="o3", model_id="m2"),
            ],
            "service_experiences": [
                {"technician_id": "t1", "normalized_purpose": "a"},
                {"technician_id": "t1", "normalized_purpose": "b"},
                {"technician_id": "t1", "normalized_purpose": "a"},
            ],
        }
    )

    nodes = snapshot.expected_counts(NODE_STAGES)
    relationships = snapshot.expected_counts(RELATIONSHIP_STAGES)

    assert nodes["SolarOffer"] == 3
    assert nodes["SolarModel"] == 2
    assert nodes["Supplier"] == 1
    assert nodes["ServiceExperience"] == 2
    assert relationships["OF_MODEL"] == 3
    assert relationships["HAS_EXPERIENCE"] == 2
    assert nodes["LocalUnit"] == 0
    assert snapshot.total_rows == 6


def test_clean_replaces_non_finite_floats_with_none():
    row = _clean({"a": nan, "b": inf, "c": 1.5, "d": "x", "e": None, "f": 3})

    assert row == {"a": None, "b": None, "c": 1.5, "d": "x", "e": None, "f": 3}


def test_valid_panel_offer_requires_positive_physical_measures_and_bounded_efficiency():
    assert _valid_panel_offer(panel_row())
    assert _valid_panel_offer(panel_row(efficiency=0.0))
    assert not _valid_panel_offer(panel_row(power_wp=None))
    assert not _valid_panel_offer(panel_row(power_wp=0))
    assert not _valid_panel_offer(panel_row(dimension=-1))
    assert not _valid_panel_offer(panel_row(weight=None))
    assert not _valid_panel_offer(panel_row(efficiency=101))
    assert not _valid_panel_offer(panel_row(efficiency=-0.1))


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query):
        self.connection.executed.append(query)
        self.rows = self.connection.responses.get(len(self.connection.executed) - 1, [])

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, responses=None):
        self.executed = []
        self.responses = responses or {}

    def cursor(self):
        return FakeCursor(self)


def test_load_snapshot_runs_every_dataset_in_order_and_sends_heartbeats():
    connection = FakeConnection({1: [panel_row(), panel_row(offer_id="o2", power_wp=0)]})
    beats = []

    snapshot = load_snapshot(connection, heartbeat=lambda: beats.append(1))

    assert len(connection.executed) == len(DATASETS)
    assert len(beats) == len(DATASETS)
    assert list(snapshot.datasets) == list(DATASETS)
    assert [row["offer_id"] for row in snapshot.rows("panel_offers")] == ["o1"]


def test_load_snapshot_works_without_heartbeat():
    snapshot = load_snapshot(FakeConnection())

    assert snapshot.total_rows == 0
