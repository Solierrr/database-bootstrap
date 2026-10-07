import pytest

from database_bootstrap.bootstrap.errors import UnsafeSnapshotError
from database_bootstrap.bootstrap.nodes import chunks
from database_bootstrap.bootstrap.validation import validate_domain_retention, validate_exact_counts


def test_exact_counts_pass_when_equal():
    validate_exact_counts({"Technician": 2, "Shift": 0}, {"Technician": 2}, "nós")


def test_exact_counts_report_each_mismatch():
    with pytest.raises(UnsafeSnapshotError) as error:
        validate_exact_counts({"Technician": 2, "Shift": 1}, {"Technician": 1}, "nós")

    message = str(error.value)
    assert "Technician: esperado 2, encontrado 1" in message
    assert "Shift: esperado 1, encontrado 0" in message


def test_retention_accepts_growth_and_small_drops():
    validate_domain_retention({"Technician": 10}, {"Technician": 6}, 0.5)
    validate_domain_retention({"Technician": 10}, {"Technician": 30}, 0.5)


def test_retention_ignores_domains_that_were_empty():
    validate_domain_retention({"Technician": 0}, {"Technician": 0}, 0.5)


def test_retention_refuses_abnormal_drop():
    with pytest.raises(UnsafeSnapshotError) as error:
        validate_domain_retention({"SolarOffer": 10, "Shift": 4}, {"SolarOffer": 2, "Shift": 4}, 0.5)

    assert "SolarOffer: 2/10" in str(error.value)
    assert "Shift" not in str(error.value)


def test_chunks_split_rows_by_batch_size():
    rows = [{"id": index} for index in range(5)]

    assert [len(batch) for batch in chunks(rows, 2)] == [2, 2, 1]
    assert list(chunks([], 2)) == []
