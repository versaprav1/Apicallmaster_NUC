"""
Module: duckdb_engine.loader

Purpose:
    High-level utilities to create, refresh, and validate a DuckDB database from
    JSON-like sources. Supports large JSON arrays, line-delimited JSON (NDJSON),
    and single-object payloads that may embed lists. The module creates a raw
    landing table and materializes a normalized view (`inventory_view`) that is
    useful for downstream analytics and indexing.

Key Concepts:
    - Ingestion pipeline: detect JSON shape → ingest into `raw_all` → build views
      → print basic stats. Ingestion is idempotent when `force_refresh` is used.
    - Shape detection: distinguishes between array, ndjson, and object payloads
      to choose efficient and resilient `read_json_auto` strategies.
    - Normalization: creates `inventory_view` to standardize common fields such as
      name, type, description, sender, and receiver for exploration.

Public API:
    - `DuckDBLoader`: Main class to load/refresh/validate the database and report
      metadata.
    - `load_json_to_duckdb`: Convenience function to perform a one-shot load.
    - CLI (`main`): Command-line interface to load, inspect, and validate DB.

Inputs/Outputs:
    - Inputs: Path to a JSON file (array, ndjson, or object with nested `data`).
    - Outputs: DuckDB file containing `raw_all` table and `inventory_view`.
    - Side effects: Creates directories for the database path if needed.

Dependencies:
    - External: `duckdb` for execution; file I/O via `pathlib`.
    - Internal: This module is self-contained but intended to be used by broader
      ingestion/extraction workflows.

Usage:
    >>> from duckdb_engine.loader import load_json_to_duckdb
    >>> ok = load_json_to_duckdb("data/interfaces.json", db_path="duckdb/wic.duckdb")
    >>> print(ok)
    True
"""

import json
import duckdb
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import argparse
import sys


class DuckDBLoader:
    """Manage DuckDB database loading, refresh, and validation.

    This class orchestrates the end-to-end ingestion pipeline from a JSON-like
    source into DuckDB, normalizes common fields into views, and exposes helper
    methods to inspect and validate the resulting database.

    Attributes:
        db_path: Filesystem path to the DuckDB database file. The parent
            directory is created automatically if it does not exist.
    """
    
    def __init__(self, db_path: str = "duckdb/wic.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_from_json(self, json_path: Union[str, Path], force_refresh: bool = False) -> bool:
        """
        Load data from JSON file into DuckDB.
        
        Args:
            json_path: Path to JSON file
            force_refresh: Whether to recreate database even if it exists
            
        Returns:
            True if successful, False otherwise
        """
        json_path = Path(json_path)
        if not json_path.exists():
            print(f"[ERROR] JSON file not found: {json_path}")
            return False
        
        # Check if database exists and force_refresh is False
        if self.db_path.exists() and not force_refresh:
            print(f"[INFO] Database already exists: {self.db_path}")
            return True
        
        try:
            # Detect JSON shape
            shape = self._detect_json_shape(json_path)
            print(f"[INFO] Detected JSON shape: {shape}")
            
            # Connect to database
            con = duckdb.connect(str(self.db_path))
            con.execute("PRAGMA threads=4")
            
            # Drop existing tables
            con.execute("DROP TABLE IF EXISTS raw_all")
            con.execute("DROP VIEW IF EXISTS inventory_view")
            
            # Ingest data
            self._ingest_data(con, json_path, shape)
            
            # Create views
            self._create_views(con)
            
            # Get statistics
            self._print_statistics(con)
            
            con.close()
            print(f"[INFO] Successfully loaded data into: {self.db_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load data: {e}")
            return False
    
    def _detect_json_shape(self, json_path: Path) -> str:
        """Detect JSON shape: 'array', 'ndjson', or 'object'."""
        try:
            with json_path.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    if s.startswith('['):
                        return 'array'
                    if s.startswith('{'):
                        # Could be object or NDJSON; peek a few lines
                        count_obj_lines = 1
                        for _ in range(10):
                            nxt = f.readline()
                            if not nxt:
                                break
                            if nxt.strip().startswith('{'):
                                count_obj_lines += 1
                        return 'ndjson' if count_obj_lines > 3 else 'object'
                    break
        except Exception as e:
            print(f"[WARN] Could not detect JSON shape: {e}")
        
        return 'array'  # Default fallback
    
    def _ingest_data(self, con: duckdb.DuckDBPyConnection, json_path: Path, shape: str) -> None:
        """Ingest data based on detected shape."""
        if shape == 'array':
            con.execute(
                "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, maximum_object_size=268435456)",
                [str(json_path)]
            )
        elif shape == 'ndjson':
            con.execute(
                "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, records=true, maximum_object_size=268435456)",
                [str(json_path)]
            )
        else:  # object
            con.execute(
                "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, maximum_object_size=268435456)",
                [str(json_path)]
            )
            # Check if it has a data column with list
            cols = [r[0] for r in con.execute("DESCRIBE raw_all").fetchall()]
            if 'data' in cols:
                con.execute("DROP TABLE IF EXISTS raw_rows")
                con.execute("CREATE TABLE raw_rows AS SELECT * FROM raw_all")
                con.execute("DROP TABLE raw_all")
                con.execute("CREATE TABLE raw_all AS SELECT * FROM (SELECT * FROM raw_rows), UNNEST(data)")
                con.execute("DROP TABLE raw_rows")
    
    def _create_views(self, con: duckdb.DuckDBPyConnection) -> None:
        """Create normalized views."""
        # Create inventory view
        con.execute("""
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
        """)
        
        # TODO: Create other entity views as needed
        # - task_view for task entities
        # - log_view for logEntry entities
        # - datasource_view for datasource entities
        # - system_view for system entities
        # - dataflow_view for dataFlow entities
    
    def _print_statistics(self, con: duckdb.DuckDBPyConnection) -> None:
        """Print database statistics."""
        try:
            # Total count
            total = con.execute("SELECT COUNT(*) FROM raw_all").fetchone()[0]
            print(f"[INFO] Total rows: {total}")
            
            # Type distribution
            dist = con.execute(
                "SELECT CAST(norm_type AS VARCHAR) AS type_id, COUNT(*) AS cnt FROM inventory_view GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            ).fetchall()
            print("[INFO] Top 10 types:")
            for row in dist:
                print(f"  {row[0]}: {row[1]}")
                
        except Exception as e:
            print(f"[WARN] Could not get statistics: {e}")
    
    def refresh_database(self, json_path: Union[str, Path]) -> bool:
        """Refresh database from JSON file."""
        return self.load_from_json(json_path, force_refresh=True)
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        info = {
            "database_path": str(self.db_path),
            "exists": self.db_path.exists(),
            "size_mb": 0,
            "tables": [],
            "views": []
        }
        
        if self.db_path.exists():
            try:
                # Get file size
                info["size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
                
                # Get tables and views
                con = duckdb.connect(str(self.db_path))
                tables = con.execute("SHOW TABLES").fetchall()
                views = con.execute("SHOW VIEWS").fetchall()
                con.close()
                
                info["tables"] = [t[0] for t in tables]
                info["views"] = [v[0] for v in views]
                
            except Exception as e:
                info["error"] = str(e)
        
        return info
    
    def validate_database(self) -> bool:
        """Validate database structure."""
        if not self.db_path.exists():
            return False
        
        try:
            con = duckdb.connect(str(self.db_path))
            
            # Check required tables/views
            required_objects = ['raw_all', 'inventory_view']
            for obj in required_objects:
                result = con.execute(f"SELECT COUNT(*) FROM {obj}").fetchone()
                if result[0] == 0:
                    print(f"[WARN] {obj} is empty")
            
            con.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Database validation failed: {e}")
            return False


def load_json_to_duckdb(json_path: Union[str, Path], db_path: str = "duckdb/wic.duckdb", force_refresh: bool = False) -> bool:
    """Load a JSON/NDJSON file into a DuckDB database in one call.

    This convenience wrapper constructs a `DuckDBLoader` and delegates to
    `DuckDBLoader.load_from_json`.

    Args:
        json_path: Path to a JSON file. Supports JSON arrays, NDJSON, or an
            object that may contain a nested list under `data`.
        db_path: Path to the target DuckDB database file. Created if missing.
        force_refresh: If True, recreates tables/views even if the DB exists.

    Returns:
        True if ingestion and view creation succeed; False otherwise.
    """
    loader = DuckDBLoader(db_path)
    return loader.load_from_json(json_path, force_refresh)


def main():
    """Command-line interface for loading and inspecting the database.

    Options:
        --input: Path to the input JSON/NDJSON file (required for load).
        --db: Output DuckDB file path (default: duckdb/wic.duckdb).
        --force: Force refresh even if the database already exists.
        --info: Print database metadata (path, size, tables, views) and exit.
        --validate: Validate presence of required tables/views and exit.
    """
    parser = argparse.ArgumentParser(description="Load JSON data into DuckDB")
    parser.add_argument("--input", required=True, help="Path to JSON file")
    parser.add_argument("--db", default="duckdb/wic.duckdb", help="Output DuckDB file path")
    parser.add_argument("--force", action="store_true", help="Force refresh even if database exists")
    parser.add_argument("--info", action="store_true", help="Show database info")
    parser.add_argument("--validate", action="store_true", help="Validate database")
    
    args = parser.parse_args()
    
    loader = DuckDBLoader(args.db)
    
    if args.info:
        info = loader.get_database_info()
        print(json.dumps(info, indent=2))
        return
    
    if args.validate:
        is_valid = loader.validate_database()
        print(f"Database valid: {is_valid}")
        return
    
    # Load data
    success = loader.load_from_json(args.input, args.force)
    if success:
        print("✅ Database loading completed successfully")
    else:
        print("❌ Database loading failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
