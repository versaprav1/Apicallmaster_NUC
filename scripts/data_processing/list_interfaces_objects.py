import duckdb
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="List interfaces and object presence from DuckDB inventory_view")
    parser.add_argument("--db", default="duckdb_engine/wic.duckdb", help="Path to DuckDB database file")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for detail rows (0 = no limit)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DuckDB database not found: {db_path}")
        return 1

    con = duckdb.connect(str(db_path))

    # Presence matrix
    presence_sql = """
    SELECT
      norm_name                                   AS interface_name,
      CAST(norm_type AS VARCHAR)                  AS type,
      (norm_sender_name IS NOT NULL)              AS has_sender,
      (norm_receiver_name IS NOT NULL)            AS has_receiver,
      COALESCE(array_length(tags), 0)    > 0       AS has_tags,
      COALESCE(array_length(metadata), 0) > 0      AS has_metadata,
      COALESCE(array_length(properties), 0) > 0    AS has_properties
    FROM inventory_view
    ORDER BY interface_name
    """

    print("\n=== Interface → Objects Presence Matrix ===\n")
    print(con.execute(presence_sql).df().to_string(index=False))

    # Aggregate summary
    summary_sql = """
    SELECT
      SUM(CASE WHEN norm_sender_name IS NOT NULL THEN 1 ELSE 0 END)  AS interfaces_with_sender,
      SUM(CASE WHEN norm_receiver_name IS NOT NULL THEN 1 ELSE 0 END) AS interfaces_with_receiver,
      SUM(CASE WHEN COALESCE(array_length(tags),0) > 0 THEN 1 ELSE 0 END)       AS interfaces_with_tags,
      SUM(CASE WHEN COALESCE(array_length(metadata),0) > 0 THEN 1 ELSE 0 END)   AS interfaces_with_metadata,
      SUM(CASE WHEN COALESCE(array_length(properties),0) > 0 THEN 1 ELSE 0 END) AS interfaces_with_properties,
      COUNT(*) AS total_interfaces
    FROM inventory_view
    """

    print("\n=== Summary ===\n")
    print(con.execute(summary_sql).df().to_string(index=False))

    # Detailed filtered view
    detail_sql = """
    SELECT
      norm_name AS interface_name,
      CAST(norm_type AS VARCHAR) AS type,
      norm_sender_name, norm_receiver_name, tags, metadata, properties
    FROM inventory_view
    WHERE
      norm_sender_name IS NOT NULL
      OR norm_receiver_name IS NOT NULL
      OR COALESCE(array_length(tags),0) > 0
      OR COALESCE(array_length(metadata),0) > 0
      OR COALESCE(array_length(properties),0) > 0
    ORDER BY interface_name
    """

    if args.limit and args.limit > 0:
        detail_sql += f" LIMIT {int(args.limit)}"

    print("\n=== Detailed Interfaces With Any Objects Present ===\n")
    print(con.execute(detail_sql).df().to_string(index=False))

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


