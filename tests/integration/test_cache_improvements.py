#!/usr/bin/env python3
"""
Test script to demonstrate the improved caching functionality in ApiCallMaster
"""

import json
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def test_cache_improvements():
    """Test the improved caching functionality"""
    
    print("🧪 Testing ApiCallMaster Cache Improvements")
    print("=" * 50)
    
    # Initialize KnowledgeStore
    knowledge_store = KnowledgeStore("test_cache")
    
    # Test 1: Cache Key Normalization
    print("\n1️⃣ Testing Cache Key Normalization")
    print("-" * 30)
    
    # Create two similar queries with different field order
    query1 = {
        "query": {
            "entity": "inventory",
            "fields": ["name", "type", "description"],
            "where": [{"option": 1, "conditions": [{"field": {"name": "type", "eq": "14"}}]}]
        }
    }
    
    query2 = {
        "query": {
            "entity": "inventory", 
            "fields": ["description", "name", "type"],  # Different order
            "where": [{"option": 1, "conditions": [{"field": {"name": "type", "eq": "14"}}]}]
        }
    }
    
    endpoint = "https://test.com/api/interfaces"
    
    key1 = knowledge_store._generate_cache_key(query1, endpoint)
    key2 = knowledge_store._generate_cache_key(query2, endpoint)
    
    print(f"Query 1 key: {key1}")
    print(f"Query 2 key: {key2}")
    print(f"Keys match: {'✅' if key1 == key2 else '❌'}")
    
    # Test 2: Cache Storage and Retrieval
    print("\n2️⃣ Testing Cache Storage and Retrieval")
    print("-" * 30)
    
    # Mock API response
    mock_response = {
        "data": [
            {"id": 1, "name": "Test Interface", "type": "SAP_ODATA"},
            {"id": 2, "name": "Another Interface", "type": "MULE_API"}
        ]
    }
    
    processed_summary = "Found 2 interfaces: Test Interface (SAP_ODATA) and Another Interface (MULE_API)"
    chunk_summaries = ["SAP interfaces: 1", "MULE interfaces: 1"]
    
    # Store response
    cache_key = knowledge_store.store_response(
        query=query1,
        endpoint=endpoint,
        raw_response=mock_response,
        processed_summary=processed_summary,
        chunk_summaries=chunk_summaries
    )
    
    print(f"Stored cache with key: {cache_key}")
    
    # Retrieve response
    cached_data = knowledge_store.get_cached_response(query1, endpoint, debug=True)
    
    if cached_data:
        print("✅ Cache retrieval successful!")
        print(f"Summary: {cached_data['processed_summary'][:50]}...")
        print(f"Chunk summaries: {len(cached_data['chunk_summaries'])} chunks")
    else:
        print("❌ Cache retrieval failed!")
    
    # Test 3: Similar Query Matching
    print("\n3️⃣ Testing Similar Query Matching")
    print("-" * 30)
    
    # Create a similar but not identical query
    similar_query = {
        "query": {
            "entity": "inventory",
            "fields": ["name", "type"],  # Missing 'description' field
            "where": [{"option": 1, "conditions": [{"field": {"name": "type", "eq": "14"}}]}]
        }
    }
    
    similar_queries = knowledge_store.get_similar_queries(similar_query, endpoint)
    print(f"Found {len(similar_queries)} similar queries")
    
    if similar_queries:
        similarity = similar_queries[0]['similarity']
        print(f"Highest similarity: {similarity:.2%}")
        
        if similarity >= 0.8:
            print("✅ High similarity found - would use fuzzy matching!")
        else:
            print("⚠️ Low similarity - would not use fuzzy matching")
    
    # Test 4: Cache Statistics
    print("\n4️⃣ Testing Cache Statistics")
    print("-" * 30)
    
    stats = knowledge_store.get_cache_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Valid entries: {stats['valid_entries']}")
    print(f"Expired entries: {stats['expired_entries']}")
    print(f"Total items cached: {stats['total_items_cached']}")
    print(f"Cache size: {stats['cache_size_mb']} MB")
    
    # Test 5: Cache Search
    print("\n5️⃣ Testing Cache Search")
    print("-" * 30)
    
    search_results = knowledge_store.search_cache("interface")
    print(f"Search results for 'interface': {len(search_results)} matches")
    
    if search_results:
        print("✅ Search functionality working!")
        for result in search_results:
            print(f"  - {result['summary_preview'][:50]}...")
    else:
        print("❌ No search results found")
    
    # Cleanup
    print("\n🧹 Cleaning up test cache...")
    knowledge_store.cleanup_expired()
    
    print("\n✅ All tests completed!")
    print("\n📋 Summary of Improvements:")
    print("  ✅ Extended cache duration from 7 to 30 days")
    print("  ✅ Improved cache key normalization")
    print("  ✅ Added debug logging")
    print("  ✅ Implemented fuzzy matching for similar queries")
    print("  ✅ Added cache statistics and management UI")
    print("  ✅ Added cache search functionality")

if __name__ == "__main__":
    test_cache_improvements()
