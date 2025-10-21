import os
from pathlib import Path
from dotenv import load_dotenv
from local_executor.loader import iter_records
from local_executor.executor import execute_query
from src.graph_store_neo4j import Neo4jGraphStore


# Relationship-rich query to extract sender/receiver, tags, properties, metadata
QUERY = {
    "query": {
        "entity": "inventory",
        "fields": [
            "id",
            "name",
            "type",
            "description",
            "sender",
            "receiver",
            "data_source",
            "properties",
            "tags",
            "metadata",
        ],
        "with": [
            {"entity": "sender", "fields": ["id", "name"]},
            {"entity": "receiver", "fields": ["id", "name"]},
            {
                "entity": "properties",
                "fields": ["type_id", "value"],
                "with": [{"entity": "type", "fields": ["name", "kind"]}],
            },
            {
                "entity": "tags",
                "fields": ["value", "tag_id"],
                "with": [{"entity": "tag", "fields": ["name"]}],
            },
            {"entity": "metadata", "fields": ["name", "value"]},
        ],
        "limit": 100000,
    }
}


def _resolve_json_path(raw: str) -> Path:
    candidates = []
    p = Path(raw)
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.append(Path.cwd() / raw)
        candidates.append(Path(__file__).resolve().parent / raw)
        candidates.append(Path(__file__).resolve().parent / "23-09-2025.json")
    for c in candidates:
        if c.exists():
            return c
    # Fallback: list nearby JSONs for a helpful error
    root = Path(__file__).resolve().parent
    nearby = ", ".join(x.name for x in root.glob("*.json"))
    raise FileNotFoundError(f"Could not find local JSON. Tried: {', '.join(str(c) for c in candidates)}. Nearby JSON files: {nearby}")


def main():
    # Load .env so NEO4J_* and LOCAL_JSON_PATH are available
    try:
        load_dotenv()
    except Exception:
        pass
    raw_path = os.getenv("LOCAL_JSON_PATH", "23-09-2025.json")
    resolved = _resolve_json_path(raw_path)
    print(f"Loading local data from: {resolved}")

    # Stream and execute a relationship-rich query over local JSON
    # Materialize to a list so we can slice/batch and report counts reliably
    records = list(execute_query(iter_records(str(resolved)), QUERY))
    print(f"Preparing to ingest {len(records)} records into Neo4j...")
    if records:
        sample_keys = list(records[0].keys())
        print(f"Sample record keys: {sample_keys}")

    # Ingest into Neo4j
    store = Neo4jGraphStore()
    try:
        store.ensure_constraints()
        print("Constraints ensured. Starting upsert...")
        store.bulk_upsert(records)
        # Post-ingest sanity count
        total_nodes = store.run_tx("MATCH (n) RETURN count(n) AS total")
        try:
            total = total_nodes[0]["total"] if total_nodes else 0
        except Exception:
            total = 0
        print(f"Ingestion completed. Total nodes now in DB: {total}")
    finally:
        store.close()


if __name__ == "__main__":
    main()


