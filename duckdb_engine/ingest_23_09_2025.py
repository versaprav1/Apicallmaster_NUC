import argparse
import json
import sys
from pathlib import Path

import duckdb


def detect_shape(json_path: Path) -> str:
    """Detect JSON shape: 'array', 'ndjson', or 'object'."""
    # Heuristic: try to sniff first non-empty char
    with json_path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith('['):
                return 'array'
            if s.startswith('{'):
                # Could be object or NDJSON; peek a few lines to see multiple JSON objects
                # If many lines start with '{', assume NDJSON
                count_obj_lines = 1
                for _ in range(10):
                    nxt = f.readline()
                    if not nxt:
                        break
                    if nxt.strip().startswith('{'):
                        count_obj_lines += 1
                return 'ndjson' if count_obj_lines > 3 else 'object'
            # Fallback
            break
    return 'array'


def ingest(json_path: Path, db_path: Path) -> None:
    con = duckdb.connect(str(db_path))
    con.execute("PRAGMA threads=4")

    shape = detect_shape(json_path)
    print(f"[INFO] Detected JSON shape: {shape}")

    # Drop old tables
    con.execute("DROP TABLE IF EXISTS raw_all")

    # Ingest
    if shape == 'array':
        con.execute(
            "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, maximum_object_size=268435456)",
            [str(json_path)],
        )
    elif shape == 'ndjson':
        con.execute(
            "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, records=true, maximum_object_size=268435456)",
            [str(json_path)],
        )
    else:  # object (maybe contains data array)
        con.execute(
            "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, maximum_object_size=268435456)",
            [str(json_path)],
        )
        # If it has a data column with list, unnest to rows table
        cols = [r[0] for r in con.execute("DESCRIBE raw_all").fetchall()]
        if 'data' in cols:
            con.execute("DROP TABLE IF EXISTS raw_rows")
            con.execute("CREATE TABLE raw_rows AS SELECT * FROM raw_all")
            # Unnest list elements in data into raw_all
            con.execute("DROP TABLE raw_all")
            con.execute("CREATE TABLE raw_all AS SELECT * FROM (SELECT * FROM raw_rows), UNNEST(data)")
            con.execute("DROP TABLE raw_rows")

    # Basic counts
    total = con.execute("SELECT COUNT(*) FROM raw_all").fetchone()[0]
    print(f"[INFO] Rows ingested: {total}")

    # Create a normalized inventory view - data is already at top level
    con.execute("DROP VIEW IF EXISTS inventory_view")
    con.execute(
        """
        CREATE VIEW inventory_view AS
        SELECT 
            r.name AS norm_name,
            r.type AS norm_type,
            r.description AS norm_description,
            r.sender->>'name' AS norm_sender_name,
            r.receiver->>'name' AS norm_receiver_name,
            r.metadata,
            r.properties,
            r.tags,
            r.sender,
            r.receiver
        FROM raw_all AS r
        """
    )

    # Type distribution
    try:
        dist = con.execute(
            "SELECT CAST(norm_type AS VARCHAR) AS type_id, COUNT(*) AS cnt FROM inventory_view GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        print("[INFO] Type distribution (type_id, count):")
        for row in dist:
            print("  ", row)
    except Exception as e:
        print(f"[WARN] Could not compute type distribution: {e}")

    con.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest JSON into DuckDB and print stats")
    parser.add_argument("--input", required=True, help="Path to JSON file (array, NDJSON, or object-with-data)")
    parser.add_argument("--db", default="ApiCallMaster/duckdb/wic.duckdb", help="Output DuckDB file path")
    args = parser.parse_args()

    json_path = Path(args.input).resolve()
    db_path = Path(args.db).resolve()

    if not json_path.exists():
        print(f"[ERROR] Input file not found: {json_path}")
        sys.exit(1)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    ingest(json_path, db_path)
    print(f"[INFO] Ingestion completed. Database: {db_path}")


if __name__ == "__main__":
    main()
