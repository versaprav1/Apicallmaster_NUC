#!/usr/bin/env python3
"""
Simple script to ingest local JSON data into Neo4j cloud database.
This script reads your local JSON file and imports it into your Neo4j cloud instance.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()

def find_json_file():
    """Find the JSON file to ingest"""
    # Try different possible locations
    possible_files = [
        "23-09-2025.json",
        "data.json", 
        "interfaces.json",
        "all_data.json"
    ]
    
    for filename in possible_files:
        if Path(filename).exists():
            return filename
    
    # If not found, ask user
    print("Available JSON files:")
    for json_file in Path(".").glob("*.json"):
        print(f"  - {json_file}")
    
    return input("Enter the JSON filename: ").strip()

def load_json_data(filename):
    """Load JSON data from file"""
    print(f"Loading data from {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    return data

def transform_data_for_neo4j(data):
    """Transform JSON data into Neo4j-friendly format"""
    print("Transforming data for Neo4j...")
    
    transformed = []
    for i, record in enumerate(data):
        if i % 1000 == 0:
            print(f"  Processed {i}/{len(data)} records...")
        
        # Extract basic fields
        transformed_record = {
            "id": record.get("id", f"record_{i}"),
            "name": record.get("name", ""),
            "type": record.get("type", ""),
            "description": record.get("description", ""),
        }
        
        # Extract sender information
        if "sender" in record and record["sender"]:
            sender = record["sender"]
            if isinstance(sender, dict):
                transformed_record["sender_name"] = sender.get("name", "")
                transformed_record["sender_id"] = sender.get("id", "")
            else:
                transformed_record["sender_name"] = str(sender)
        
        # Extract receiver information  
        if "receiver" in record and record["receiver"]:
            receiver = record["receiver"]
            if isinstance(receiver, dict):
                transformed_record["receiver_name"] = receiver.get("name", "")
                transformed_record["receiver_id"] = receiver.get("id", "")
            else:
                transformed_record["receiver_name"] = str(receiver)
        
        # Extract metadata
        if "metadata" in record and record["metadata"]:
            transformed_record["metadata"] = record["metadata"]
        
        # Extract properties
        if "properties" in record and record["properties"]:
            transformed_record["properties"] = record["properties"]
        
        # Extract tags
        if "tags" in record and record["tags"]:
            transformed_record["tags"] = record["tags"]
        
        transformed.append(transformed_record)
    
    print(f"Transformed {len(transformed)} records")
    return transformed

def main():
    """Main ingestion function"""
    print("Neo4j Cloud Data Ingestion")
    print("=" * 50)
    
    # Check environment variables
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("ERROR: Missing Neo4j credentials in .env file")
        print("Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return
    
    print(f"Connecting to: {neo4j_uri}")
    print(f"User: {neo4j_user}")
    
    # Find and load JSON file
    json_file = find_json_file()
    if not Path(json_file).exists():
        print(f"ERROR: File not found: {json_file}")
        return
    
    data = load_json_data(json_file)
    if not data:
        print("ERROR: No data loaded")
        return
    
    # Transform data
    transformed_data = transform_data_for_neo4j(data)
    
    # Connect to Neo4j and ingest
    print("\nConnecting to Neo4j cloud...")
    try:
        store = Neo4jGraphStore()
        
        print("Setting up constraints...")
        store.ensure_constraints()
        
        print("Starting bulk upsert...")
        store.bulk_upsert(transformed_data)
        
        # Verify ingestion
        print("Verifying ingestion...")
        result = store.run_tx("MATCH (n) RETURN count(n) as total")
        total_nodes = result[0]['total'] if result else 0
        
        print(f"\nSUCCESS: Ingestion completed!")
        print(f"Total nodes in database: {total_nodes}")
        
        # Show some sample queries
        print("\nSample queries you can now run:")
        print("  - 'Which systems send data to Salesforce?'")
        print("  - 'What is the shortest path from SAP to Azure?'")
        print("  - 'Find interfaces connected to MuleSoft'")
        
        store.close()
        
    except Exception as e:
        print(f"ERROR during ingestion: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check your Neo4j cloud credentials")
        print("  2. Ensure your Neo4j instance is running")
        print("  3. Verify network connectivity")

if __name__ == "__main__":
    main()
