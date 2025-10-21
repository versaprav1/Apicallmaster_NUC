#!/usr/bin/env python3
"""
Script to create sender/receiver relationships in Neo4j.
This script reads the existing nodes and creates SENT_BY and RECEIVED_BY relationships.
"""

import os
from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()

def create_sender_receiver_relationships():
    """Create SENT_BY and RECEIVED_BY relationships"""
    print("Creating sender/receiver relationships...")
    
    try:
        store = Neo4jGraphStore()
        
        # First, let's see what we have
        print("Checking existing data...")
        
        # Count interfaces
        result = store.run_tx("MATCH (i:Interface) RETURN count(i) as count")
        interface_count = result[0]['count'] if result else 0
        print(f"Found {interface_count} interfaces")
        
        # Count systems
        result = store.run_tx("MATCH (s:System) RETURN count(s) as count")
        system_count = result[0]['count'] if result else 0
        print(f"Found {system_count} systems")
        
        # Create SENT_BY relationships
        print("Creating SENT_BY relationships...")
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
        print("Creating RECEIVED_BY relationships...")
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
        
        # Verify relationships
        print("Verifying relationships...")
        result = store.run_tx("MATCH ()-[r:SENT_BY]->() RETURN count(r) as count")
        sent_count = result[0]['count'] if result else 0
        
        result = store.run_tx("MATCH ()-[r:RECEIVED_BY]->() RETURN count(r) as count")
        received_count = result[0]['count'] if result else 0
        
        print(f"Total SENT_BY relationships: {sent_count}")
        print(f"Total RECEIVED_BY relationships: {received_count}")
        
        # Show some sample relationships
        print("\nSample relationships:")
        result = store.run_tx("""
        MATCH (i:Interface)-[:SENT_BY]->(s:System)
        RETURN i.name as interface, s.name as sender
        LIMIT 5
        """)
        
        for record in result:
            print(f"  {record['interface']} -> SENT_BY -> {record['sender']}")
        
        result = store.run_tx("""
        MATCH (i:Interface)-[:RECEIVED_BY]->(s:System)
        RETURN i.name as interface, s.name as receiver
        LIMIT 5
        """)
        
        for record in result:
            print(f"  {record['interface']} -> RECEIVED_BY -> {record['receiver']}")
        
        store.close()
        print("\nSUCCESS: Relationships created successfully!")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    create_sender_receiver_relationships()
