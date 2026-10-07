import pytest

from database_bootstrap.bootstrap import state
from database_bootstrap.bootstrap.errors import SyncInProgressError, UnsafeSnapshotError
from database_bootstrap.bootstrap.runner import run
from database_bootstrap.clients.postgres import snapshot_connection
from database_bootstrap.main import EXIT_SYNC_IN_PROGRESS, main
from database_bootstrap.sync.extract import GraphSnapshot, load_snapshot

pytestmark = pytest.mark.integration

EXPECTED_NODES = {
    "LocalUnit": 2,
    "SolarModel": 1,
    "Supplier": 1,
    "SolarOffer": 1,
    "Profession": 2,
    "Technician": 1,
    "TechnicianAffiliation": 1,
    "Shift": 1,
    "TechnicalService": 2,
    "ServiceExperience": 1,
}

EXPECTED_RELATIONSHIPS = {
    "OF_MODEL": 1,
    "FROM_SUPPLIER": 1,
    "REGISTERED_AS": 1,
    "OF_TECHNICIAN": 1,
    "HAS_SHIFT": 1,
    "HAS_EXPERIENCE": 1,
    "ASSIGNED_TO": 2,
}


def loader(settings):
    def load(heartbeat):
        with snapshot_connection(settings) as connection:
            return load_snapshot(connection, heartbeat)

    return load


def graph_state(driver, settings):
    with driver.session(database=settings.neo4j_database) as session:
        record = session.run(
            "MATCH (s:SyncState {source: $source}) "
            "RETURN s.active_version AS active, s.previous_version AS previous, "
            "s.sync_in_progress AS locked, coalesce(s.pending_cleanup_versions, []) AS pending",
            source=state.SOURCE,
        ).single()
    return dict(record) if record else None


def count_versions(driver, settings):
    with driver.session(database=settings.neo4j_database) as session:
        return {
            record["version"]: record["total"]
            for record in session.run(
                "MATCH (n) WHERE n.source = $source AND n.sync_version IS NOT NULL "
                "RETURN n.sync_version AS version, count(n) AS total",
                source=state.SOURCE,
            )
        }


def test_extract_reads_only_eligible_rows_from_the_real_schema(seeded_postgres):
    with snapshot_connection(seeded_postgres) as connection:
        snapshot = load_snapshot(connection)

    assert {name: len(rows) for name, rows in snapshot.datasets.items()} == {
        "local_units": 2,
        "panel_offers": 1,
        "professions": 2,
        "technicians": 1,
        "registrations": 1,
        "affiliations": 1,
        "shifts": 1,
        "technical_services": 2,
        "service_experiences": 1,
        "assignments": 2,
    }

    offer = snapshot.rows("panel_offers")[0]
    assert offer["inventory_quantity"] == 15
    assert offer["effective_availability"] == 15
    assert offer["accepted_proposal_quantity"] == 3
    assert offer["unit_price_cents"] == 75055
    assert offer["subscription_active"] is True
    assert offer["supplier_latitude"] == pytest.approx(-23.55052)

    technician = snapshot.rows("technicians")[0]
    assert technician["average_rating_global"] == pytest.approx(4.5)
    assert technician["review_count_global"] == 1
    assert technician["assigned_service_count_global"] == 2
    assert technician["completed_service_count_global"] == 1
    assert technician["active_workload"] == 1

    registration = snapshot.rows("registrations")[0]
    assert registration["valid_certification_count"] == 1
    assert registration["certification_names"] == ["NR-10"]

    units = {row["location_type"]: row for row in snapshot.rows("local_units")}
    assert units["HOUSE"]["geolocation_count"] == 1
    assert units["BUILDING"]["geolocation_count"] == 2
    assert units["BUILDING"]["latitude"] is None

    experience = snapshot.rows("service_experiences")[0]
    assert experience["normalized_purpose"] == "instalacao solar"


def test_run_projects_the_snapshot_and_activates_it(seeded_postgres, empty_graph):
    summary = run(seeded_postgres, empty_graph, loader(seeded_postgres))

    assert summary.nodes == EXPECTED_NODES
    assert summary.relationships == EXPECTED_RELATIONSHIPS

    active = graph_state(empty_graph, seeded_postgres)
    assert active["active"] == summary.sync_version
    assert active["locked"] is False

    with empty_graph.session(database=seeded_postgres.neo4j_database) as session:
        nodes, relationships = state.snapshot_counts(session, summary.sync_version)
        offer = session.run(
            "MATCH (o:SolarOffer)-[:OF_MODEL]->(m:SolarModel), (o)-[:FROM_SUPPLIER]->(s:Supplier) "
            "WHERE o.sync_version = $version "
            "RETURN o.effective_availability AS availability, m.brand AS brand, s.trade_name AS supplier",
            version=summary.sync_version,
        ).single()
        registration = session.run(
            "MATCH (:Technician)-[r:REGISTERED_AS]->(p:Profession) WHERE r.sync_version = $version "
            "RETURN p.name AS profession, r.certification_names AS certifications",
            version=summary.sync_version,
        ).single()
    assert nodes == EXPECTED_NODES
    assert relationships == EXPECTED_RELATIONSHIPS
    assert dict(offer) == {"availability": 15, "brand": "Canadian", "supplier": "Solar Forte"}
    assert dict(registration) == {"profession": "Engenheiro Eletricista", "certifications": ["NR-10"]}


def test_repeated_runs_are_idempotent_and_clean_old_versions(seeded_postgres, empty_graph):
    versions = [run(seeded_postgres, empty_graph, loader(seeded_postgres)).sync_version for _ in range(3)]

    current = graph_state(empty_graph, seeded_postgres)
    assert current["active"] == versions[2]
    assert current["previous"] == versions[1]

    remaining = count_versions(empty_graph, seeded_postgres)
    assert versions[0] not in remaining
    assert set(remaining) == {versions[1], versions[2]}
    assert remaining[versions[2]] == sum(EXPECTED_NODES.values())


def test_empty_snapshot_is_refused_and_keeps_the_active_version(seeded_postgres, empty_graph):
    first = run(seeded_postgres, empty_graph, loader(seeded_postgres))

    with pytest.raises(UnsafeSnapshotError):
        run(seeded_postgres, empty_graph, lambda heartbeat: GraphSnapshot({}))

    current = graph_state(empty_graph, seeded_postgres)
    assert current["active"] == first.sync_version
    assert current["locked"] is False
    assert set(count_versions(empty_graph, seeded_postgres)) == {first.sync_version}


def test_abnormal_domain_drop_is_refused(seeded_postgres, empty_graph):
    first = run(seeded_postgres, empty_graph, loader(seeded_postgres))

    def shrunken(heartbeat):
        snapshot = loader(seeded_postgres)(heartbeat)
        return GraphSnapshot({**snapshot.datasets, "panel_offers": []})

    with pytest.raises(UnsafeSnapshotError, match="SolarOffer"):
        run(seeded_postgres, empty_graph, shrunken)

    assert graph_state(empty_graph, seeded_postgres)["active"] == first.sync_version

    follow_up = run(seeded_postgres, empty_graph, loader(seeded_postgres))
    assert graph_state(empty_graph, seeded_postgres)["active"] == follow_up.sync_version


def test_concurrent_run_is_rejected_while_the_lock_is_held(seeded_postgres, empty_graph):
    with empty_graph.session(database=seeded_postgres.neo4j_database) as session:
        state.begin_sync(session, "held-by-another-run", 600)
        try:
            with pytest.raises(SyncInProgressError):
                run(seeded_postgres, empty_graph, loader(seeded_postgres))
        finally:
            state.release_lock(session, "held-by-another-run")


def test_main_runs_end_to_end_and_reports_lock_contention(seeded_postgres, empty_graph):
    assert main() == 0
    assert graph_state(empty_graph, seeded_postgres)["active"] is not None

    with empty_graph.session(database=seeded_postgres.neo4j_database) as session:
        state.begin_sync(session, "held-by-another-run", 600)
        try:
            assert main() == EXIT_SYNC_IN_PROGRESS
        finally:
            state.release_lock(session, "held-by-another-run")
