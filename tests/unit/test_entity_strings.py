#!/usr/bin/env python3
"""
Test script to verify entity string extraction and persistent storage.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_store import KnowledgeStore
import json

def test_entity_strings():
    """Test entity string extraction and storage."""
    
    print("🧪 Testing Entity String Extraction")
    print("=" * 50)
    
    # Initialize knowledge store
    ks = KnowledgeStore()
    
    # Test 1: Check if knowledge_entities directory exists
    entities_dir = ks.cache_dir.parent / "knowledge_entities"
    print(f"📁 Knowledge entities directory: {entities_dir}")
    print(f"   Exists: {entities_dir.exists()}")
    
    if not entities_dir.exists():
        print("   Creating directory...")
        entities_dir.mkdir(exist_ok=True)
    
    # Test 2: Check existing cache entries
    print(f"\n📊 Current cache entries:")
    index_file = ks.cache_dir / "index.json"
    if index_file.exists():
        with open(index_file, 'r') as f:
            index = json.load(f)
            for key, entry in index.items():
                print(f"   {key}: {entry.get('endpoint', 'unknown')} ({entry.get('total_items', 0)} items)")
    else:
        print("   No cache entries found")
    
    # Test 3: Check if any cache entries have entity_strings
    print(f"\n🔍 Checking for entity_strings in cache entries:")
    entries = ks.get_all_valid_entries()
    entity_strings_found = 0
    
    for entry in entries:
        if isinstance(entry, dict) and 'entity_strings' in entry:
            entity_strings_found += 1
            print(f"   ✅ Found entity_strings in cache entry: {len(entry.get('entity_strings', []))} strings")
        else:
            print(f"   ❌ No entity_strings in cache entry")
    
    print(f"\n📈 Summary: {entity_strings_found} cache entries have entity_strings")
    
    # Test 4: Check persistent entity files
    print(f"\n📄 Checking persistent entity files:")
    if entities_dir.exists():
        entity_files = list(entities_dir.glob("*.jsonl"))
        if entity_files:
            for file in entity_files:
                try:
                    with open(file, 'r') as f:
                        lines = f.readlines()
                        print(f"   📄 {file.name}: {len(lines)} lines")
                except Exception as e:
                    print(f"   ❌ Error reading {file.name}: {e}")
        else:
            print("   No .jsonl files found in knowledge_entities directory")
    
    # Test 5: Simulate entity string extraction
    print(f"\n🧪 Testing entity string extraction with sample data:")
    sample_response = {
        "data": [
            {"id": "1", "name": "Test Interface 1", "type": "SAP", "description": "Test description 1"},
            {"id": "2", "name": "Test Interface 2", "type": "MULE", "description": "Test description 2"},
            {"id": "3", "name": "Test Interface 3", "type": "REST", "description": "Test description 3"}
        ]
    }
    
    extracted_strings = ks._extract_entity_strings(sample_response)
    print(f"   Extracted {len(extracted_strings)} entity strings:")
    for i, string in enumerate(extracted_strings[:3]):  # Show first 3
        print(f"     {i+1}: {string}")
    
    if len(extracted_strings) > 3:
        print(f"     ... and {len(extracted_strings) - 3} more")
    
    print(f"\n💡 Recommendations:")
    if entity_strings_found == 0:
        print("   - No cache entries have entity_strings. You need to run a fresh query")
        print("   - Try asking a new question that will trigger an API call")
        print("   - Or clear the cache and run the same query again")
    else:
        print("   - Some cache entries have entity_strings. Check if they're being persisted")
    
    if not entity_files:
        print("   - No persistent entity files found. Run a fresh query to create them")
    
    return entity_strings_found, len(entity_files) if entity_files else 0

if __name__ == "__main__":
    test_entity_strings()
