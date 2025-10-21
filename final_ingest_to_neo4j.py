#!/usr/bin/env python3
"""
Final ingestion script that properly formats data for Neo4jGraphStore
"""

import json
import re
import os
from pathlib import Path
from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()

def extract_sender_receiver_from_name(name):
    """Extract sender and receiver from interface name using patterns"""
    sender = None
    receiver = None
    
    # Common patterns in interface names
    patterns = [
        # Pattern: "from X to Y"
        r'from\s+([A-Za-z0-9\s]+?)\s+to\s+([A-Za-z0-9\s]+?)(?:\s|$)',
        # Pattern: "X to Y"
        r'([A-Za-z0-9\s]+?)\s+to\s+([A-Za-z0-9\s]+?)(?:\s|$)',
        # Pattern: "X | Y" (pipe separator)
        r'([A-Za-z0-9\s]+?)\s*\|\s*([A-Za-z0-9\s]+?)(?:\s|$)',
        # Pattern: "X -> Y" (arrow)
        r'([A-Za-z0-9\s]+?)\s*->\s*([A-Za-z0-9\s]+?)(?:\s|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            sender = match.group(1).strip()
            receiver = match.group(2).strip()
            break
    
    # Clean up common words
    if sender:
        sender = re.sub(r'\b(interface|api|service|system)\b', '', sender, flags=re.IGNORECASE).strip()
    if receiver:
        receiver = re.sub(r'\b(interface|api|service|system)\b', '', receiver, flags=re.IGNORECASE).strip()
    
    return sender, receiver

def transform_data_for_neo4j(data):
    """Transform JSON data into Neo4jGraphStore-compatible format"""
    print("Transforming data for Neo4jGraphStore...")
    
    transformed = []
    sender_receiver_count = 0
    
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
        
        # Extract sender/receiver from name
        name = record.get("name", "")
        sender, receiver = extract_sender_receiver_from_name(name)
        
        # Format sender/receiver as objects (what Neo4jGraphStore expects)
        if sender:
            transformed_record["sender"] = {"name": sender}
            sender_receiver_count += 1
        
        if receiver:
            transformed_record["receiver"] = {"name": receiver}
            sender_receiver_count += 1
        
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
    print(f"Found sender/receiver info in {sender_receiver_count} records")
    return transformed

def main():
    """Main ingestion function"""
    print("Final Neo4j Cloud Data Ingestion")
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
    
    # Load JSON file
    json_file = "23-09-2025.json"
    if not Path(json_file).exists():
        print(f"ERROR: File not found: {json_file}")
        return
    
    print(f"Loading data from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    # Transform data
    transformed_data = transform_data_for_neo4j(data)
    
    # Connect to Neo4j and ingest
    print("\nConnecting to Neo4j cloud...")
    try:
        store = Neo4jGraphStore()
        
        print("Clearing existing data...")
        store.run_tx("MATCH (n) DETACH DELETE n")
        
        print("Setting up constraints...")
        store.ensure_constraints()
        
        print("Starting bulk upsert...")
        store.bulk_upsert(transformed_data)
        
        # Verify ingestion
        print("Verifying ingestion...")
        result = store.run_tx("MATCH (n) RETURN count(n) as total")
        total_nodes = result[0]['total'] if result else 0
        
        result = store.run_tx("MATCH ()-[r:SENT_BY]->() RETURN count(r) as count")
        sent_count = result[0]['count'] if result else 0
        
        result = store.run_tx("MATCH ()-[r:RECEIVED_BY]->() RETURN count(r) as count")
        received_count = result[0]['count'] if result else 0
        
        print(f"\nSUCCESS: Ingestion completed!")
        print(f"Total nodes in database: {total_nodes}")
        print(f"SENT_BY relationships: {sent_count}")
        print(f"RECEIVED_BY relationships: {received_count}")
        
        # Show some sample relationships
        if sent_count > 0:
            print("\nSample SENT_BY relationships:")
            result = store.run_tx("""
            MATCH (i:Interface)-[:SENT_BY]->(s:System)
            RETURN i.name as interface, s.name as sender
            LIMIT 3
            """)
            
            for record in result:
                print(f"  {record['interface'][:50]}... -> SENT_BY -> {record['sender']}")
        
        if received_count > 0:
            print("\nSample RECEIVED_BY relationships:")
            result = store.run_tx("""
            MATCH (i:Interface)-[:RECEIVED_BY]->(s:System)
            RETURN i.name as interface, s.name as receiver
            LIMIT 3
            """)
            
            for record in result:
                print(f"  {record['interface'][:50]}... -> RECEIVED_BY -> {record['receiver']}")
        
        store.close()
        
        # Test GraphRAG
        print("\nTesting GraphRAG...")
        try:
            from methods.graph_rag import run
            result, meta = run("Which systems send data to Salesforce?")
            print("GraphRAG test successful!")
            print(f"Result preview: {result[:200]}...")
        except Exception as e:
            print(f"GraphRAG test failed: {str(e)}")
        
    except Exception as e:
        print(f"ERROR during ingestion: {str(e)}")

if __name__ == "__main__":
    main()
