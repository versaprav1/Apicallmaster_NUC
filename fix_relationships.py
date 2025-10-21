#!/usr/bin/env python3
"""
Check and fix sender/receiver relationships
"""

import os
from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()

def check_and_fix_relationships():
    """Check and fix sender/receiver relationships"""
    print("Checking and fixing relationships...")
    
    try:
        store = Neo4jGraphStore()
        
        # Check if sender_name property exists
        print("Checking sender_name property...")
        result = store.run_tx("MATCH (i:Interface) WHERE i.sender_name IS NOT NULL RETURN count(i) as count")
        sender_count = result[0]['count'] if result else 0
        print(f"Interfaces with sender_name: {sender_count}")
        
        if sender_count == 0:
            print("No sender_name property found. Checking all properties...")
            result = store.run_tx("MATCH (i:Interface) RETURN keys(i) as keys LIMIT 1")
            if result:
                print(f"Available properties: {result[0]['keys']}")
        
        # Try to create relationships anyway
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
        result = store.run_tx("MATCH ()-[r:SENT_BY]->() RETURN count(r) as count")
        sent_count = result[0]['count'] if result else 0
        
        result = store.run_tx("MATCH ()-[r:RECEIVED_BY]->() RETURN count(r) as count")
        received_count = result[0]['count'] if result else 0
        
        print(f"Total SENT_BY relationships: {sent_count}")
        print(f"Total RECEIVED_BY relationships: {received_count}")
        
        store.close()
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    check_and_fix_relationships()
