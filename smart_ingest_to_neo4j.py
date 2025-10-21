#!/usr/bin/env python3
"""
Smart ingestion script that extracts sender/receiver from interface names and metadata
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

def extract_sender_receiver_from_metadata(metadata):
    """Extract sender/receiver from metadata"""
    sender = None
    receiver = None
    
    if not metadata:
        return sender, receiver
    
    for item in metadata:
        name = item.get('name', '').lower()
        value = item.get('value', '')
        
        if 'sender' in name or 'source' in name:
            sender = value
        elif 'receiver' in name or 'target' in name or 'destination' in name:
            receiver = value
    
    return sender, receiver

def transform_data_for_neo4j(data):
    """Transform JSON data into Neo4j-friendly format with sender/receiver extraction"""
    print("Transforming data for Neo4j with sender/receiver extraction...")
    
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
        sender_from_name, receiver_from_name = extract_sender_receiver_from_name(name)
        
        # Extract sender/receiver from metadata
        metadata = record.get("metadata", [])
        sender_from_metadata, receiver_from_metadata = extract_sender_receiver_from_metadata(metadata)
        
        # Use metadata values if available, otherwise use name extraction
        sender = sender_from_metadata or sender_from_name
        receiver = receiver_from_metadata or receiver_from_name
        
        if sender:
            transformed_record["sender_name"] = sender
        if receiver:
            transformed_record["receiver_name"] = receiver
        
        if sender or receiver:
            sender_receiver_count += 1
        
        # Extract metadata
        if metadata:
            transformed_record["metadata"] = metadata
        
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
    print("Smart Neo4j Cloud Data Ingestion")
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
        
        # Create sender/receiver relationships
        print("Creating sender/receiver relationships...")
        
        # Create SENT_BY relationships
        sent_by_query = """
        MATCH (i:Interface)
        WHERE i.sender_name IS NOT NULL AND i.sender_name <> ""
        MERGE (s:System {name: i.sender_name})
        MERGE (i)-[:SENT_BY]->(s)
        RETURN count(*) as created
        """
        result = store.run_tx(sent_by_query)
        sent_relationships = result[0]['created'] if result else 0
        print(f"Created {sent_relationships} SENT_BY relationships")
        
        # Create RECEIVED_BY relationships
        received_by_query = """
        MATCH (i:Interface)
        WHERE i.receiver_name IS NOT NULL AND i.receiver_name <> ""
        MERGE (s:System {name: i.receiver_name})
        MERGE (i)-[:RECEIVED_BY]->(s)
        RETURN count(*) as created
        """
        result = store.run_tx(received_by_query)
        received_relationships = result[0]['created'] if result else 0
        print(f"Created {received_relationships} RECEIVED_BY relationships")
        
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
        print("\nSample relationships:")
        result = store.run_tx("""
        MATCH (i:Interface)-[:SENT_BY]->(s:System)
        RETURN i.name as interface, s.name as sender
        LIMIT 3
        """)
        
        for record in result:
            print(f"  {record['interface'][:50]}... -> SENT_BY -> {record['sender']}")
        
        result = store.run_tx("""
        MATCH (i:Interface)-[:RECEIVED_BY]->(s:System)
        RETURN i.name as interface, s.name as receiver
        LIMIT 3
        """)
        
        for record in result:
            print(f"  {record['interface'][:50]}... -> RECEIVED_BY -> {record['receiver']}")
        
        store.close()
        
    except Exception as e:
        print(f"ERROR during ingestion: {str(e)}")

if __name__ == "__main__":
    main()
