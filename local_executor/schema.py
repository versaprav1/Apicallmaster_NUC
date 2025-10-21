from typing import Any, Literal

EntityName = Literal["inventory", "task", "logEntry", "datasource", "system", "dataFlow"]


def detect_entity(record: Any) -> EntityName | None:
    """Heuristically detect entity type from a single record.
    This is best-effort; execution will still validate required fields.
    """
    if not isinstance(record, dict):
        return None
    # Log entry characteristics
    if all(k in record for k in ("level", "message")):
        return "logEntry"
    # Task characteristics
    if any(k in record for k in ("start_date", "runs")):
        return "task"
    # Inventory characteristics
    if any(k in record for k in ("type", "sender_name", "receiver_name")):
        return "inventory"
    # Datasource/system/dataFlow could require domain-specific keys; fallback None
    return None


