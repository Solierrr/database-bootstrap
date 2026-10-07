import pytest

import main

pytestmark = pytest.mark.integration

EXPECTED_STAGES = {
    "nodes/local_units": 2,
    "nodes/solar_models": 1,
    "nodes/suppliers": 1,
    "nodes/solar_offers": 1,
    "nodes/professions": 2,
    "nodes/technicians": 1,
    "nodes/affiliations": 1,
    "nodes/shifts": 1,
    "nodes/technical_services": 2,
    "nodes/service_experiences": 1,
    "relationships/offer_model": 1,
    "relationships/offer_supplier": 1,
    "relationships/technician_profession": 1,
    "relationships/affiliation_technician": 1,
    "relationships/technician_shift": 1,
    "relationships/technician_experience": 1,
    "relationships/affiliation_service": 2,
}

NODES_PER_VERSION = 13


def execute(driver, settings, query, **parameters):
    with driver.session(database=settings.neo4j_database) as session:
        return session.run(query, **parameters).data()


def graph_state(driver, settings):
    rows = execute(
        driver,
        settings,
        "MATCH (s:SyncState {source: $source}) "
        "RETURN s.active_version AS active, s.previous_version AS previous, "
        "s.sync_in_progress AS locked",
        source=main.SOURCE,
    )
    return rows[0] if rows else None


def count_versions(driver, settings):
    rows = execute(
        driver,
        settings,
        "MATCH (n) WHERE n.source = $source AND n.sync_version IS NOT NULL "
        "RETURN n.sync_version AS version, count(n) AS total",
        source=main.SOURCE,
    )
    return {row["version"]: row["total"] for row in rows}


def test_extract_reads_only_eligible_rows_from_the_real_schema(seeded_postgres):
    with main.psycopg.connect(**seeded_postgres.postgres, row_factory=main.dict_row) as connection:
        rows = main.extract(connection)

    assert {name: len(items) for name, items in rows.items()} == {
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

    offer = rows["panel_offers"][0]
    assert offer["inventory_quantity"] == 15
    assert offer["effective_availability"] == 15
    assert offer["accepted_proposal_quantity"] == 3
    assert offer["unit_price_cents"] == 75055
    assert offer["subscription_active"] is True
    assert offer["supplier_latitude"] == pytest.approx(-23.55052)

    technician = rows["technicians"][0]
    assert technician["average_rating_global"] == pytest.approx(4.5)
    assert technician["review_count_global"] == 1
    assert technician["assigned_service_count_global"] == 2
    assert technician["completed_service_count_global"] == 1
    assert technician["active_workload"] == 1

    registration = rows["registrations"][0]
    assert registration["valid_certification_count"] == 1
    assert registration["certification_names"] == ["NR-10"]

    units = {row["location_type"]: row for row in rows["local_units"]}
    assert units["HOUSE"]["geolocation_count"] == 1
    assert units["BUILDING"]["geolocation_count"] == 2
    assert units["BUILDING"]["latitude"] is None

    assert rows["service_experiences"][0]["normalized_purpose"] == "instalacao solar"


def test_run_projects_the_snapshot_and_activates_it(seeded_postgres, empty_graph):
    version, counts = main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))

    assert counts == EXPECTED_STAGES

    current = graph_state(empty_graph, seeded_postgres)
    assert current["active"] == version
    assert current["locked"] is False
    assert count_versions(empty_graph, seeded_postgres) == {version: NODES_PER_VERSION}

    offer = execute(
        empty_graph,
        seeded_postgres,
        "MATCH (o:SolarOffer)-[:OF_MODEL]->(m:SolarModel), (o)-[:FROM_SUPPLIER]->(s:Supplier) "
        "RETURN o.effective_availability AS availability, m.brand AS brand, s.trade_name AS supplier",
    )
    registration = execute(
        empty_graph,
        seeded_postgres,
        "MATCH (:Technician)-[r:REGISTERED_AS]->(p:Profession) "
        "RETURN p.name AS profession, r.certification_names AS certifications",
    )
    assert offer == [{"availability": 15, "brand": "Canadian", "supplier": "Solar Forte"}]
    assert registration == [{"profession": "Engenheiro Eletricista", "certifications": ["NR-10"]}]


def test_repeated_runs_are_idempotent_and_clean_old_versions(seeded_postgres, empty_graph):
    versions = [
        main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))[0] for _ in range(3)
    ]

    current = graph_state(empty_graph, seeded_postgres)
    assert current["active"] == versions[2]
    assert current["previous"] == versions[1]
    assert count_versions(empty_graph, seeded_postgres) == {
        versions[1]: NODES_PER_VERSION,
        versions[2]: NODES_PER_VERSION,
    }


def test_empty_snapshot_is_refused_and_keeps_the_active_version(seeded_postgres, empty_graph):
    first, _ = main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))

    with pytest.raises(main.UnsafeSnapshotError):
        main.run(seeded_postgres, empty_graph, lambda heartbeat: {})

    current = graph_state(empty_graph, seeded_postgres)
    assert current["active"] == first
    assert current["locked"] is False
    assert set(count_versions(empty_graph, seeded_postgres)) == {first}


def test_abnormal_domain_drop_is_refused(seeded_postgres, empty_graph):
    first, _ = main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))

    def shrunken(heartbeat):
        rows = main.postgres_loader(seeded_postgres)(heartbeat)
        return {**rows, "panel_offers": []}

    with pytest.raises(main.UnsafeSnapshotError, match="SolarOffer"):
        main.run(seeded_postgres, empty_graph, shrunken)

    assert graph_state(empty_graph, seeded_postgres)["active"] == first
    assert set(count_versions(empty_graph, seeded_postgres)) == {first}

    follow_up, _ = main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))
    assert graph_state(empty_graph, seeded_postgres)["active"] == follow_up


def test_relationship_rows_without_endpoints_are_refused(seeded_postgres, empty_graph):
    def orphaned(heartbeat):
        rows = main.postgres_loader(seeded_postgres)(heartbeat)
        return {**rows, "assignments": [{**row, "service_id": "missing"} for row in rows["assignments"]]}

    with pytest.raises(main.UnsafeSnapshotError, match="affiliation_service"):
        main.run(seeded_postgres, empty_graph, orphaned)

    assert graph_state(empty_graph, seeded_postgres)["active"] is None


def test_concurrent_run_is_rejected_while_the_lock_is_held(seeded_postgres, empty_graph):
    with empty_graph.session(database=seeded_postgres.neo4j_database) as session:
        main._begin(session, "held-by-another-run", 600)
        try:
            with pytest.raises(main.SyncInProgressError):
                main.run(seeded_postgres, empty_graph, main.postgres_loader(seeded_postgres))
        finally:
            main._run(session, "release_lock", sync_version="held-by-another-run").consume()


def test_main_runs_end_to_end_and_reports_lock_contention(seeded_postgres, empty_graph):
    assert main.main() == 0
    assert graph_state(empty_graph, seeded_postgres)["active"] is not None

    with empty_graph.session(database=seeded_postgres.neo4j_database) as session:
        main._begin(session, "held-by-another-run", 600)
        try:
            assert main.main() == main.EXIT_SYNC_IN_PROGRESS
        finally:
            main._run(session, "release_lock", sync_version="held-by-another-run").consume()
