#!/usr/bin/env python3
"""
Debug script to test entity string extraction and persistence.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_store import KnowledgeStore
import json

def debug_entity_strings():
    """Debug entity string extraction and persistence."""
    
    print("🔍 Debugging Entity String Extraction")
    print("=" * 50)
    
    # Initialize knowledge store
    ks = KnowledgeStore()
    
    # Test 1: Check directories
    print(f"📁 Cache directory: {ks.cache_dir}")
    print(f"   Exists: {ks.cache_dir.exists()}")
    print(f"📁 Entity store directory: {ks.entity_store_dir}")
    print(f"   Exists: {ks.entity_store_dir.exists()}")
    
    # Test 2: Check current cache entry
    print(f"\n📊 Current cache entries:")
    index_file = ks.cache_dir / "index.json"
    if index_file.exists():
        with open(index_file, 'r') as f:
            index = json.load(f)
            for key, entry in index.items():
                print(f"   {key}: {entry.get('endpoint', 'unknown')}")
                
                # Check if this cache entry has entity_strings
                cache_file = ks.cache_dir / f"{key}.json"
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                        if 'entity_strings' in cache_data:
                            print(f"     ✅ Has entity_strings: {len(cache_data['entity_strings'])} strings")
                        else:
                            print(f"     ❌ No entity_strings in cache")
    else:
        print("   No cache entries found")
    
    # Test 3: Test entity string extraction with sample data
    print(f"\n🧪 Testing entity string extraction:")
    sample_response = {
        "data": [
            {"id": "1", "name": "Test Interface 1", "type": "SAP", "description": "Test description 1"},
            {"id": "2", "name": "Test Interface 2", "type": "MULE", "description": "Test description 2"},
            {"id": "3", "name": "Test Interface 3", "type": "REST", "description": "Test description 3"}
        ]
    }
    
    extracted_strings = ks._extract_entity_strings(sample_response)
    print(f"   Extracted {len(extracted_strings)} entity strings:")
    for i, string in enumerate(extracted_strings):
        print(f"     {i+1}: {string}")
    
    # Test 4: Test persistent storage
    print(f"\n💾 Testing persistent storage:")
    test_endpoint = "https://test.example.com/api/test"
    test_strings = ["test1", "test2", "test3"]
    
    try:
        written_count = ks.append_entity_strings_persistent(test_endpoint, test_strings)
        print(f"   ✅ Wrote {written_count} strings to persistent store")
        
        # Check if file was created
        entity_file = ks._entity_store_path(test_endpoint)
        print(f"   📄 Entity file: {entity_file}")
        print(f"   📄 Exists: {entity_file.exists()}")
        
        if entity_file.exists():
            with open(entity_file, 'r') as f:
                lines = f.readlines()
                print(f"   📄 Content ({len(lines)} lines):")
                for i, line in enumerate(lines):
                    print(f"     {i+1}: {line.strip()}")
        
    except Exception as e:
        print(f"   ❌ Error writing to persistent store: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check if the issue is with the actual API response format
    print(f"\n🔍 Checking actual API response format:")
    if index_file.exists():
        with open(index_file, 'r') as f:
            index = json.load(f)
            for key, entry in index.items():
                cache_file = ks.cache_dir / f"{key}.json"
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                        print(f"   Cache entry {key}:")
                        print(f"     - Has raw_response_summary: {'raw_response_summary' in cache_data}")
                        if 'raw_response_summary' in cache_data:
                            summary = cache_data['raw_response_summary']
                            print(f"     - Total items: {summary.get('total_items', 'unknown')}")
                            print(f"     - Has full data: {summary.get('has_full_data', 'unknown')}")
                        print(f"     - Has entity_strings: {'entity_strings' in cache_data}")
                        if 'entity_strings' in cache_data:
                            print(f"     - Entity strings count: {len(cache_data['entity_strings'])}")
                        break  # Only check first entry

if __name__ == "__main__":
    debug_entity_strings()
