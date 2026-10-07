import re

import pytest

import main

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


@pytest.fixture(scope="module")
def dataset_names():
    return list(main.queries())


@pytest.fixture(scope="module")
def all_stages():
    return main.stages()


def test_every_dataset_resolves_its_fragments(dataset_names):
    assert len(dataset_names) == 10
    for dataset in dataset_names:
        text = main.queries()[dataset]

        assert "-- include:" not in text
        assert re.search(r"\bSELECT\b", text)
        assert text.count("(") == text.count(")")


def test_shared_fragments_are_inlined_where_requested():
    assert "eligible_technician AS (" in main.queries()["technicians"]
    assert "technician.status = 'APPROVED'" in main.queries()["shifts"]
    assert "users.active IS TRUE" in main.queries()["shifts"]


def test_every_sql_query_reads_only(dataset_names):
    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b", re.IGNORECASE)
    for dataset in dataset_names:
        assert not forbidden.search(main.queries()[dataset]), dataset


def test_sql_references_only_core_tables_or_its_own_ctes(dataset_names):
    for dataset in dataset_names:
        text = main.queries()[dataset]
        referenced = {match.group(1) for match in re.finditer(r"\b(?:FROM|JOIN)\s+([a-z_]+)", text)}
        ctes = {match.group(1) for match in re.finditer(r"\b([a-z_]+)\s+AS\s+\(", text)}

        assert referenced <= CORE_TABLES | ctes, (dataset, referenced - CORE_TABLES - ctes)


def test_stages_run_nodes_before_relationships(all_stages):
    groups = [stage.name.split("/")[0] for stage in all_stages]

    assert groups == sorted(groups, key=["nodes", "relationships"].index)
    assert groups.count("nodes") == 10
    assert groups.count("relationships") == 7


def test_every_stage_reads_a_known_dataset_and_reports_merged_rows(all_stages, dataset_names):
    for stage in all_stages:
        assert stage.dataset in dataset_names, stage.name
        assert "UNWIND $rows AS row" in stage.query, stage.name
        assert stage.query.rstrip().endswith("RETURN count(*) AS merged"), stage.name
        assert "$sync_version" in stage.query, stage.name


def test_every_node_stage_has_a_uniqueness_constraint(all_stages):
    schema = main.cypher("schema")
    for stage in all_stages:
        if not stage.name.startswith("nodes/"):
            continue
        label = re.search(r"MERGE \(\w+:(\w+)", stage.query).group(1)
        assert f"(n:{label})" in schema, stage.name


def test_stage_without_dataset_header_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "graphs" / "nodes").mkdir(parents=True)
    (tmp_path / "graphs" / "relationships").mkdir()
    (tmp_path / "graphs" / "nodes" / "broken.cypher").write_text(
        "UNWIND $rows AS row RETURN count(*) AS merged"
    )
    monkeypatch.setattr(main, "SRC", tmp_path)

    with pytest.raises(ValueError, match="broken.cypher"):
        main.stages()


def test_schema_has_one_statement_per_semicolon():
    statements = [statement.strip() for statement in main.cypher("schema").split(";") if statement.strip()]

    assert len(statements) == 16
    assert all(statement.startswith(("CREATE CONSTRAINT", "CREATE INDEX")) for statement in statements)


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
        self.rows = [{"id": len(self.connection.executed)}]

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


def test_extract_runs_every_dataset_and_sends_heartbeats(dataset_names):
    connection = FakeConnection()
    beats = []

    rows = main.extract(connection, heartbeat=lambda: beats.append(1))

    assert list(rows) == dataset_names
    assert len(connection.executed) == len(dataset_names)
    assert len(beats) == len(dataset_names)


def test_extract_works_without_heartbeat():
    assert len(main.extract(FakeConnection())) == 10


def test_tolerate_logs_and_swallows_failures(caplog):
    with main._tolerate("falhou %s", "aqui"):
        raise RuntimeError("boom")

    assert "falhou aqui" in caplog.text
