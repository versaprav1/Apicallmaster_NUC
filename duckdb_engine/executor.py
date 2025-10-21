"""
DuckDB Query Executor

Executes SQL queries against DuckDB and returns API-shaped responses.
Handles result formatting, error handling, and diagnostics.
"""

import json
import duckdb
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from .translator import DuckDBTranslator


class DuckDBExecutor:
    """Executes SQL queries against DuckDB and formats responses."""
    
    def __init__(self, db_path: str = "duckdb/wic.duckdb"):
        self.db_path = Path(db_path)
        self.translator = DuckDBTranslator()
        
    def execute_query(self, whint_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute WHINT query against DuckDB.
        
        Args:
            whint_query: WHINT API query structure
            
        Returns:
            API-shaped response dict or None if error
        """
        try:
            # Validate query
            is_valid, error_msg = self.translator.validate_query(whint_query)
            if not is_valid:
                return self._create_error_response(f"Invalid query: {error_msg}")
            
            # Translate to SQL
            sql, params = self.translator.translate(whint_query)
            
            # Execute SQL
            results = self._execute_sql(sql, params)
            
            if results is None:
                return self._create_error_response("SQL execution failed")
            
            # Format as API response
            return self._format_api_response(results, whint_query)
            
        except Exception as e:
            return self._create_error_response(f"Execution error: {str(e)}")
    
    def _execute_sql(self, sql: str, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Execute SQL query with parameters."""
        if not self.db_path.exists():
            return None
        
        try:
            con = duckdb.connect(str(self.db_path))
            
            # Convert named parameters to positional parameters for DuckDB
            if params:
                # Replace :param_name with ? and create parameter list
                param_list = []
                param_names = list(params.keys())
                for param_name in param_names:
                    sql = sql.replace(f":{param_name}", "?")
                    param_list.append(params[param_name])
                
                result = con.execute(sql, param_list).fetchall()
                columns = [desc[0] for desc in con.description]
            else:
                result = con.execute(sql).fetchall()
                columns = [desc[0] for desc in con.description]
            
            con.close()
            
            # Convert to list of dicts
            return [dict(zip(columns, row)) for row in result]
            
        except Exception as e:
            print(f"SQL execution error: {e}")
            print(f"SQL: {sql}")
            print(f"Params: {params}")
            return None
    
    def _format_api_response(self, results: List[Dict[str, Any]], original_query: Dict[str, Any]) -> Dict[str, Any]:
        """Format results as API response."""
        # Get query info
        query_part = original_query.get('query', {})
        entity = query_part.get('entity', 'inventory')
        limit = query_part.get('limit')  # No default limit
        offset = query_part.get('offset', 0)
        
        # Transform results to match API format
        formatted_results = []
        for row in results:
            formatted_row = self._transform_row(row, entity)
            formatted_results.append(formatted_row)
        
        # Create API response structure
        response = {
            "data": formatted_results,
            "total": len(formatted_results),
            "offset": offset,
            "entity": entity
        }
        
        # Only include limit if it was specified in the query
        if limit is not None:
            response["limit"] = limit
        
        return response
    
    def _transform_row(self, row: Dict[str, Any], entity: str) -> Dict[str, Any]:
        """Transform database row to API format."""
        if entity == 'inventory':
            # Map normalized fields back to API format
            transformed = {}
            
            # Basic fields
            if 'norm_name' in row:
                transformed['name'] = row['norm_name']
            if 'norm_type' in row:
                transformed['type'] = row['norm_type']
            if 'norm_description' in row:
                transformed['description'] = row['norm_description']
            if 'norm_sender_name' in row:
                transformed['sender_name'] = row['norm_sender_name']
            if 'norm_receiver_name' in row:
                transformed['receiver_name'] = row['norm_receiver_name']
            
            # Complex fields (keep as-is)
            if 'metadata' in row and row['metadata'] is not None:
                transformed['metadata'] = row['metadata']
            if 'properties' in row and row['properties'] is not None:
                transformed['properties'] = row['properties']
            if 'tags' in row and row['tags'] is not None:
                transformed['tags'] = row['tags']
            if 'sender' in row and row['sender'] is not None:
                transformed['sender'] = row['sender']
            if 'receiver' in row and row['receiver'] is not None:
                transformed['receiver'] = row['receiver']
            
            return transformed
        else:
            # For other entities, return as-is for now
            return row
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "error": error_message,
            "data": [],
            "total": 0
        }
    
    def get_diagnostics(self, whint_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get diagnostic information for debugging."""
        try:
            # Translate query
            sql, params = self.translator.translate(whint_query)
            
            # Get type distribution
            type_dist = self._get_type_distribution()
            
            # Get sample data
            sample_data = self._get_sample_data()
            
            return {
                "translated_sql": sql,
                "sql_params": params,
                "type_distribution": type_dist,
                "sample_data": sample_data,
                "database_path": str(self.db_path),
                "database_exists": self.db_path.exists()
            }
            
        except Exception as e:
            return {
                "error": f"Diagnostic error: {str(e)}",
                "database_path": str(self.db_path),
                "database_exists": self.db_path.exists()
            }
    
    def _get_type_distribution(self) -> List[Tuple[str, int]]:
        """Get type distribution from database."""
        if not self.db_path.exists():
            return []
        
        try:
            con = duckdb.connect(str(self.db_path))
            result = con.execute(
                "SELECT CAST(norm_type AS VARCHAR) AS type_id, COUNT(*) AS cnt FROM inventory_view GROUP BY 1 ORDER BY 2 DESC LIMIT 20"
            ).fetchall()
            con.close()
            return result
        except Exception:
            return []
    
    def _get_sample_data(self) -> List[Dict[str, Any]]:
        """Get sample data from database."""
        if not self.db_path.exists():
            return []
        
        try:
            con = duckdb.connect(str(self.db_path))
            result = con.execute(
                "SELECT norm_name, norm_type, norm_description FROM inventory_view LIMIT 5"
            ).fetchall()
            columns = [desc[0] for desc in con.description]
            con.close()
            return [dict(zip(columns, row)) for row in result]
        except Exception:
            return []

    def get_all_data(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Return all normalized inventory records from inventory_view.

        This provides a simple, raw list of dictionaries suitable for
        downstream processing (e.g., Graph RAG ingestion), matching
        the commonly used field names in the application layer.
        """
        if not self.db_path.exists():
            return []

        try:
            con = duckdb.connect(str(self.db_path))
            base_sql = (
                "SELECT "
                "  norm_name       AS name,"
                "  norm_type       AS type,"
                "  norm_description AS description,"
                "  norm_sender_name AS sender_name,"
                "  norm_receiver_name AS receiver_name,"
                "  metadata,"
                "  properties,"
                "  tags,"
                "  sender,"
                "  receiver "
                "FROM inventory_view "
                "ORDER BY norm_name "
            )

            if limit is not None:
                sql = f"{base_sql} LIMIT {int(limit)} OFFSET {int(offset)}"
            else:
                sql = base_sql

            rows = con.execute(sql).fetchall()
            columns = [desc[0] for desc in con.description]
            con.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception:
            return []
    
    def get_interfaces_objects_matrix(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get interfaces-to-objects presence matrix with summary and details.
        
        Returns dict with:
        - presence_matrix: list of dicts with has_sender/receiver/tags/metadata/properties per interface
        - summary: counts of interfaces with each object type
        - detailed: interfaces with any objects present (optional limit)
        """
        if not self.db_path.exists():
            return {"error": "Database not found", "presence_matrix": [], "summary": {}, "detailed": []}
        
        try:
            con = duckdb.connect(str(self.db_path))
            
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
            
            presence_result = con.execute(presence_sql).fetchall()
            presence_columns = [desc[0] for desc in con.description]
            presence_matrix = [dict(zip(presence_columns, row)) for row in presence_result]
            
            # Summary
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
            
            summary_result = con.execute(summary_sql).fetchone()
            summary_columns = [desc[0] for desc in con.description]
            summary = dict(zip(summary_columns, summary_result))
            
            # Detailed (interfaces with any objects)
            detail_sql = """
            SELECT
              norm_name AS interface_name,
              CAST(norm_type AS VARCHAR) AS type,
              norm_sender_name, norm_receiver_name,
              COALESCE(array_length(tags), 0) AS tag_count,
              COALESCE(array_length(metadata), 0) AS metadata_count,
              COALESCE(array_length(properties), 0) AS property_count
            FROM inventory_view
            WHERE
              norm_sender_name IS NOT NULL
              OR norm_receiver_name IS NOT NULL
              OR COALESCE(array_length(tags),0) > 0
              OR COALESCE(array_length(metadata),0) > 0
              OR COALESCE(array_length(properties),0) > 0
            ORDER BY interface_name
            """
            
            if limit and limit > 0:
                detail_sql += f" LIMIT {int(limit)}"
            
            detail_result = con.execute(detail_sql).fetchall()
            detail_columns = [desc[0] for desc in con.description]
            detailed = [dict(zip(detail_columns, row)) for row in detail_result]
            
            con.close()
            
            return {
                "presence_matrix": presence_matrix,
                "summary": summary,
                "detailed": detailed
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "presence_matrix": [],
                "summary": {},
                "detailed": []
            }


def execute_whint_query(whint_query: Dict[str, Any], db_path: str = "duckdb/wic.duckdb") -> Optional[Dict[str, Any]]:
    """
    Convenience function to execute WHINT query against DuckDB.
    
    Args:
        whint_query: WHINT API query structure
        db_path: Path to DuckDB database
        
    Returns:
        API-shaped response dict or None if error
    """
    executor = DuckDBExecutor(db_path)
    return executor.execute_query(whint_query)


if __name__ == "__main__":
    # Test the executor
    test_query = {
        "query": {
            "entity": "inventory",
            "fields": ["name", "type", "description"],
            "where": [{
                "option": 1,
                "conditions": [{
                    "field": {
                        "name": "type",
                        "eq": "21"
                    }
                }]
            }],
            "limit": 5
        }
    }
    
    executor = DuckDBExecutor()
    result = executor.execute_query(test_query)
    print("Result:", json.dumps(result, indent=2))
    
    # Test diagnostics
    diagnostics = executor.get_diagnostics(test_query)
    print("\nDiagnostics:", json.dumps(diagnostics, indent=2))
