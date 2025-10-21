#!/usr/bin/env python3
"""
Debug the ingestion process to find where it's failing.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Windows compatibility fix
import socket
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAMILY

def debug_ingestion():
    print("=== Debugging Ingestion Process ===")
    
    # 1. Check if JSON file exists
    json_path = Path("23-09-2025.json")
    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        print("Looking for JSON files in current directory...")
        json_files = list(Path(".").glob("*.json"))
        if json_files:
            print("Found JSON files:")
            for f in json_files:
                print(f"  - {f}")
        else:
            print("No JSON files found in current directory")
        return
    
    print(f"✓ JSON file found: {json_path}")
    print(f"  Size: {json_path.stat().st_size} bytes")
    
    # 2. Check if we can import required modules
    try:
        from local_executor.loader import iter_records
        print("✓ local_executor.loader imported successfully")
    except Exception as e:
        print(f"❌ Failed to import local_executor.loader: {e}")
        return
    
    try:
        from local_executor.executor import execute_query
        print("✓ local_executor.executor imported successfully")
    except Exception as e:
        print(f"❌ Failed to import local_executor.executor: {e}")
        return
    
    try:
        from src.graph_store_neo4j import Neo4jGraphStore
        print("✓ Neo4jGraphStore imported successfully")
    except Exception as e:
        print(f"❌ Failed to import Neo4jGraphStore: {e}")
        return
    
    # 3. Test JSON file reading
    try:
        print("\n=== Testing JSON file reading ===")
        records = list(iter_records(str(json_path)))
        print(f"✓ Successfully read {len(records)} records from JSON")
        
        if records:
            print("Sample record keys:", list(records[0].keys()))
            print("Sample record:", {k: v for k, v in list(records[0].items())[:5]})
        else:
            print("❌ No records found in JSON file")
            return
            
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        return
    
    # 4. Test Neo4j connection
    try:
        print("\n=== Testing Neo4j connection ===")
        store = Neo4jGraphStore()
        print("✓ Neo4jGraphStore created successfully")
        
        # Test a simple query
        result = store.run_tx("RETURN 1 as test")
        test_value = result[0]["test"] if result else None
        print(f"✓ Neo4j connection test successful: {test_value}")
        
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return
    
    # 5. Test query execution
    try:
        print("\n=== Testing query execution ===")
        QUERY = {
            "query": {
                "entity": "inventory",
                "fields": [
                    "id", "name", "type", "description",
                    "sender", "receiver", "data_source",
                    "tags", "properties", "metadata"
                ]
            }
        }
        
        from local_executor.executor import execute_query
        query_results = list(execute_query(iter_records(str(json_path)), QUERY))
        print(f"✓ Query execution successful: {len(query_results)} results")
        
        if query_results:
            print("Sample query result keys:", list(query_results[0].keys()))
        else:
            print("❌ No results from query execution")
            return
            
    except Exception as e:
        print(f"❌ Query execution failed: {e}")
        return
    
    print("\n=== All checks passed! ===")
    print("The ingestion should work. Try running the ingestion script again.")

if __name__ == "__main__":
    debug_ingestion()
