"""
Neo4j wrapper with Windows compatibility fixes.
This module handles the Windows socket compatibility issue before importing Neo4j.
"""

import socket
import sys

# Windows compatibility fix for Neo4j driver
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAMILY

# Now import Neo4j
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Neo4j not available: {e}")
    NEO4J_AVAILABLE = False
    GraphDatabase = None

def create_driver(uri, auth=None, **kwargs):
    """Create a Neo4j driver with error handling"""
    if not NEO4J_AVAILABLE:
        raise ImportError("Neo4j driver not available")
    
    try:
        return GraphDatabase.driver(uri, auth=auth, **kwargs)
    except Exception as e:
        raise ConnectionError(f"Failed to create Neo4j driver: {e}")

def test_connection(uri, auth=None):
    """Test Neo4j connection"""
    if not NEO4J_AVAILABLE:
        return False, "Neo4j driver not available"
    
    try:
        driver = create_driver(uri, auth)
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()
            driver.close()
            return True, f"Connection successful: {test_value}"
    except Exception as e:
        return False, f"Connection failed: {e}"

if __name__ == "__main__":
    # Test the wrapper
    print("Testing Neo4j wrapper...")
    print(f"Neo4j available: {NEO4J_AVAILABLE}")
    
    if NEO4J_AVAILABLE:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'pass')
        
        success, message = test_connection(uri, (user, password))
        print(f"Connection test: {success}")
        print(f"Message: {message}")

