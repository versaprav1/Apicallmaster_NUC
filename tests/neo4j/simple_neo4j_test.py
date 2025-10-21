#!/usr/bin/env python3
"""
Simple Neo4j connection test - run this manually to test your connection.
"""

# Windows compatibility fix
import socket
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAMILY

from neo4j import GraphDatabase

# Test with the exact credentials from your Docker command
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"  # This is what you set in Docker

print(f"Testing connection to: {uri}")
print(f"User: {user}")
print(f"Password: {password}")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    print("✓ Driver created successfully")
    
    with driver.session() as session:
        result = session.run("RETURN 'Hello Neo4j!' as message")
        record = result.single()
        print(f"✓ Query result: {record['message']}")
        
        # Test database info
        result = session.run("CALL dbms.components() YIELD name, versions, edition")
        for record in result:
            print(f"✓ Database: {record['name']} {record['versions'][0]} ({record['edition']})")
    
    driver.close()
    print("✓ Connection test successful!")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure Neo4j container is running: docker ps")
    print("2. Check if you can access http://localhost:7474 in browser")
    print("3. Try logging in with username 'neo4j' and password 'your_password'")


