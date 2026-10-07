from __future__ import annotations

from collections.abc import Mapping

from database_bootstrap.bootstrap.errors import UnsafeSnapshotError


def validate_exact_counts(expected: Mapping[str, int], actual: Mapping[str, int], entity_type: str) -> None:
    mismatches = [
        f"{name}: esperado {expected_count}, encontrado {actual.get(name, 0)}"
        for name, expected_count in expected.items()
        if actual.get(name, 0) != expected_count
    ]
    if mismatches:
        raise UnsafeSnapshotError(f"Validação de {entity_type} do snapshot falhou: " + "; ".join(mismatches))


def validate_domain_retention(
    active_counts: Mapping[str, int],
    new_counts: Mapping[str, int],
    minimum_ratio: float,
) -> None:
    drops = [
        f"{name}: {new_counts.get(name, 0)}/{active_count}"
        for name, active_count in active_counts.items()
        if active_count > 0 and new_counts.get(name, 0) / active_count < minimum_ratio
    ]
    if drops:
        raise UnsafeSnapshotError("Snapshot recusado por queda anormal de domínio: " + "; ".join(drops))
