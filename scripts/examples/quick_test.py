#!/usr/bin/env python3
"""
Quick test to verify imports work
"""

print("Testing imports...")

try:
    from src.nlp_processor import NLPProcessor
    print("✅ NLPProcessor import successful")
except Exception as e:
    print(f"❌ NLPProcessor import failed: {e}")

try:
    from src.method_router import MethodRouter
    print("✅ MethodRouter import successful")
except Exception as e:
    print(f"❌ MethodRouter import failed: {e}")

try:
    from src.graph_store_neo4j import Neo4jGraphStore
    print("✅ Neo4jGraphStore import successful")
except Exception as e:
    print(f"❌ Neo4jGraphStore import failed: {e}")

print("Import test completed!")


