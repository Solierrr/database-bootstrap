import re

import pytest

from database_bootstrap import queries
from database_bootstrap.sync.domains import DATASETS, NODE_STAGES, RELATIONSHIP_STAGES


@pytest.mark.parametrize("dataset", DATASETS)
def test_every_dataset_has_a_resolved_sql_file(dataset):
    text = queries.sql(dataset)

    assert "-- include:" not in text
    assert re.search(r"\bSELECT\b", text)
    assert text.count("(") == text.count(")")


def test_shared_fragments_are_inlined_where_requested():
    technicians = queries.sql("technicians")
    shifts = queries.sql("shifts")

    assert "eligible_technician AS (" in technicians
    assert "technician.status = 'APPROVED'" in shifts
    assert "users.active IS TRUE" in shifts


def test_every_sql_query_reads_only():
    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b", re.IGNORECASE)
    for dataset in DATASETS:
        assert not forbidden.search(queries.sql(dataset)), dataset


CORE_TABLES = {
    "certification",
    "company",
    "geolocalization",
    "inventory",
    "local_unit",
    "model",
    "offer",
    "person",
    "profession",
    "professional_registration",
    "professional_review",
    "proposal",
    "proposal_item",
    "service_executor",
    "shift",
    "subscription",
    "supplier",
    "technical_project",
    "technical_service",
    "technician",
    "technician_affiliation",
    "users",
}


@pytest.mark.parametrize("dataset", DATASETS)
def test_sql_references_only_core_tables_or_its_own_ctes(dataset):
    text = queries.sql(dataset)
    referenced = {match.group(1) for match in re.finditer(r"\b(?:FROM|JOIN)\s+([a-z_]+)", text)}
    ctes = {match.group(1) for match in re.finditer(r"\b([a-z_]+)\s+AS\s+\(", text)}

    assert referenced <= CORE_TABLES | ctes, referenced - CORE_TABLES - ctes


@pytest.mark.parametrize("stage", NODE_STAGES, ids=lambda stage: stage.name)
def test_node_stage_cypher_targets_its_label(stage):
    text = queries.cypher("nodes", stage.query)

    assert "UNWIND $rows AS row" in text
    assert f":{stage.name} " in text or f":{stage.name}{{" in text
    assert "graph_key" in text
    assert "$sync_version" in text


@pytest.mark.parametrize("stage", RELATIONSHIP_STAGES, ids=lambda stage: stage.name)
def test_relationship_stage_cypher_targets_its_type(stage):
    text = queries.cypher("relationships", stage.query)

    assert "UNWIND $rows AS row" in text
    assert f":{stage.name}" in text
    assert "MERGE" in text


def test_stages_reference_known_datasets_and_have_unique_names():
    names = [stage.name for stage in (*NODE_STAGES, *RELATIONSHIP_STAGES)]

    assert len(names) == len(set(names))
    for stage in (*NODE_STAGES, *RELATIONSHIP_STAGES):
        assert stage.dataset in DATASETS
        assert stage.key


def test_schema_statements_are_split_per_statement():
    constraints = queries.cypher_statements("schema", "constraints")
    indexes = queries.cypher_statements("schema", "indexes")

    assert len(constraints) == 11
    assert all(statement.startswith("CREATE CONSTRAINT") for statement in constraints)
    assert all(statement.startswith("CREATE INDEX") for statement in indexes)
    for stage in NODE_STAGES:
        assert any(f"(n:{stage.name})" in statement for statement in constraints), stage.name
