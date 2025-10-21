#!/usr/bin/env python3
"""
Simple Neo4j connection test to verify authentication and basic connectivity.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Windows compatibility fix for Neo4j driver
import socket
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAMILY

try:
    from neo4j import GraphDatabase
    print("✓ Neo4j driver imported successfully")
except Exception as e:
    print(f"✗ Failed to import Neo4j driver: {e}")
    sys.exit(1)

def test_connection():
    """Test basic Neo4j connection and authentication."""
    
    # Get connection details
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    
    print(f"Connecting to: {uri}")
    print(f"User: {user}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    
    if not password:
        print("✗ NEO4J_PASSWORD environment variable not set")
        return False
    
    try:
        # Create driver
        driver = GraphDatabase.driver(uri, auth=(user, password))
        print("✓ Driver created successfully")
        
        # Test connectivity
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                print("✓ Connection test successful")
                
                # Test database info
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                for record in result:
                    print(f"✓ Database: {record['name']} {record['versions'][0]} ({record['edition']})")
                
                return True
            else:
                print("✗ Connection test failed")
                return False
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    finally:
        try:
            driver.close()
        except:
            pass

if __name__ == "__main__":
    print("Testing Neo4j connection...")
    success = test_connection()
    sys.exit(0 if success else 1)


