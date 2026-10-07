from __future__ import annotations

import re
from functools import cache
from importlib import resources

_INCLUDE = re.compile(r"^--\s*include:\s*(\S+)\s*$", re.MULTILINE)


def _read(relative_path: str) -> str:
    return resources.files(__package__).joinpath(relative_path).read_text(encoding="utf-8")


@cache
def sql(name: str) -> str:
    text = _read(f"postgres/{name}.sql")
    return _INCLUDE.sub(lambda match: _read(f"postgres/{match.group(1)}").strip(), text)


@cache
def cypher(group: str, name: str) -> str:
    return _read(f"neo4j/{group}/{name}.cypher")


@cache
def cypher_statements(group: str, name: str) -> tuple[str, ...]:
    return tuple(statement.strip() for statement in cypher(group, name).split(";") if statement.strip())
