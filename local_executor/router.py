from typing import Any, Iterable, Iterator, Literal
from .schema import detect_entity, EntityName


def select_collection(records: Iterable[Any], logical_endpoint: str) -> Iterator[Any]:
    """Select a stream of records approximating the routed collection.
    logical_endpoint examples: '/interfaces', '/interfaces/sap', '/tasks', '/logs', '/datasources', '/systems', '/dataflows'
    """
    # Coarse routing by endpoint keyword; fall back to detection
    endpoint = logical_endpoint.lower()

    for rec in records:
        e = detect_entity(rec)

        if "/logs" in endpoint:
            if e == "logEntry":
                yield rec
            continue
        if "/tasks" in endpoint:
            if e == "task":
                yield rec
            continue
        if "/interfaces" in endpoint or "/inventory" in endpoint:
            if e == "inventory":
                yield rec
            continue

        # Fallback: if endpoint is ambiguous, yield what matches detection
        if e is not None:
            yield rec


