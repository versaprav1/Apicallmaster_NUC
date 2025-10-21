#!/usr/bin/env python3
"""
Fix script to extract entity strings from existing cache and persist them.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_store import KnowledgeStore
import json

def fix_entity_strings():
    """Extract entity strings from existing cache and persist them."""
    
    print("🔧 Fixing Entity String Persistence")
    print("=" * 50)
    
    # Initialize knowledge store
    ks = KnowledgeStore()
    
    # Get all cache entries
    entries = ks.get_all_valid_entries()
    
    print(f"📊 Found {len(entries)} cache entries")
    
    for i, entry in enumerate(entries):
        print(f"\n🔍 Processing cache entry {i+1}:")
        
        if isinstance(entry, dict) and 'entity_strings' in entry:
            entity_strings = entry['entity_strings']
            endpoint = entry.get('endpoint', 'unknown')
            
            print(f"   📄 Endpoint: {endpoint}")
            print(f"   📊 Entity strings: {len(entity_strings)}")
            
            if entity_strings:
                try:
                    # Try to persist the entity strings
                    written_count = ks.append_entity_strings_persistent(endpoint, entity_strings)
                    print(f"   ✅ Wrote {written_count} strings to persistent store")
                    
                    # Check if file was created
                    entity_file = ks._entity_store_path(endpoint)
                    print(f"   📄 Entity file: {entity_file}")
                    print(f"   📄 Exists: {entity_file.exists()}")
                    
                    if entity_file.exists():
                        with open(entity_file, 'r') as f:
                            lines = f.readlines()
                            print(f"   📄 File has {len(lines)} lines")
                            if lines:
                                print(f"   📄 First line: {lines[0].strip()}")
                                print(f"   📄 Last line: {lines[-1].strip()}")
                    
                except Exception as e:
                    print(f"   ❌ Error persisting entity strings: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"   ⚠️  No entity strings to persist")
        else:
            print(f"   ❌ No entity_strings in cache entry")
    
    print(f"\n🎉 Fix completed!")
    
    # Show final status
    print(f"\n📁 Final status:")
    if ks.entity_store_dir.exists():
        entity_files = list(ks.entity_store_dir.glob("*.jsonl"))
        if entity_files:
            for file in entity_files:
                try:
                    with open(file, 'r') as f:
                        lines = f.readlines()
                        print(f"   📄 {file.name}: {len(lines)} lines")
                except Exception as e:
                    print(f"   ❌ Error reading {file.name}: {e}")
        else:
            print("   📄 No .jsonl files found")

if __name__ == "__main__":
    fix_entity_strings()


