#!/usr/bin/env python3
"""
Check the actual data structure in Neo4j
"""

import os
from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()

def check_data_structure():
    """Check what data we actually have"""
    print("Checking data structure...")
    
    try:
        store = Neo4jGraphStore()
        
        # Check interface properties
        print("Interface properties:")
        result = store.run_tx("MATCH (i:Interface) RETURN keys(i) as keys LIMIT 1")
        if result:
            print(f"  Properties: {result[0]['keys']}")
        
        # Check sample interface data
        print("\nSample interface data:")
        result = store.run_tx("MATCH (i:Interface) RETURN i.name, i.sender_name, i.receiver_name, i.type LIMIT 3")
        for record in result:
            print(f"  Name: {record['i.name']}")
            print(f"  Sender: {record['i.sender_name']}")
            print(f"  Receiver: {record['i.receiver_name']}")
            print(f"  Type: {record['i.type']}")
            print("  ---")
        
        # Check if we have any sender/receiver data
        print("\nChecking for sender/receiver data:")
        result = store.run_tx("MATCH (i:Interface) WHERE i.sender_name IS NOT NULL RETURN count(i) as count")
        sender_count = result[0]['count'] if result else 0
        print(f"  Interfaces with sender_name: {sender_count}")
        
        result = store.run_tx("MATCH (i:Interface) WHERE i.receiver_name IS NOT NULL RETURN count(i) as count")
        receiver_count = result[0]['count'] if result else 0
        print(f"  Interfaces with receiver_name: {receiver_count}")
        
        store.close()
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    check_data_structure()
