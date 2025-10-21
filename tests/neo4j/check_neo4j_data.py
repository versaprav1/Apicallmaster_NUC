#!/usr/bin/env python3
"""
Check what data is in Neo4j after ingestion.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Windows compatibility fix
import socket
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAMILY

from neo4j import GraphDatabase

def check_data():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'your_password')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # Check total nodes
        result = session.run("MATCH (n) RETURN count(n) as total")
        total = result.single()['total']
        print(f"Total nodes in database: {total}")
        
        if total == 0:
            print("❌ Database is empty - ingestion may have failed")
            return
        
        # Check node types
        result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
        print("\nNode types:")
        for record in result:
            labels = record['labels']
            count = record['count']
            print(f"  {labels}: {count}")
        
        # Check relationships
        result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
        print("\nRelationship types:")
        for record in result:
            rel_type = record['rel_type']
            count = record['count']
            print(f"  {rel_type}: {count}")
        
        # Show sample data
        print("\nSample Interface nodes:")
        result = session.run("MATCH (i:Interface) RETURN i.name, i.id LIMIT 5")
        for record in result:
            print(f"  {record['i.name']} (ID: {record['i.id']})")
    
    driver.close()

if __name__ == "__main__":
    check_data()


