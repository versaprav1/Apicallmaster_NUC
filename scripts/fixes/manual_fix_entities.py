#!/usr/bin/env python3
"""
Manual fix to extract entity strings from cache and persist them with proper encoding.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_store import KnowledgeStore
import json

def manual_fix_entities():
    """Manually extract and persist entity strings."""
    
    print("🔧 Manual Entity String Fix")
    print("=" * 40)
    
    # Initialize knowledge store
    ks = KnowledgeStore()
    
    # Get the cache entry
    entries = ks.get_all_valid_entries()
    
    if not entries:
        print("❌ No cache entries found")
        return
    
    entry = entries[0]  # Get first entry
    print(f"📊 Processing cache entry with {len(entry.get('entity_strings', []))} entity strings")
    
    if 'entity_strings' not in entry:
        print("❌ No entity_strings in cache entry")
        return
    
    entity_strings = entry['entity_strings']
    endpoint = entry.get('endpoint', 'unknown')
    
    print(f"📄 Endpoint: {endpoint}")
    print(f"📊 Entity strings: {len(entity_strings)}")
    
    # Get the file path
    entity_file = ks._entity_store_path(endpoint)
    print(f"📄 Target file: {entity_file}")
    
    # Write entity strings with proper encoding
    try:
        with open(entity_file, 'w', encoding='utf-8') as f:
            for i, entity_string in enumerate(entity_strings):
                # Clean the string and write it
                clean_string = str(entity_string).replace('\n', ' ').replace('\r', ' ')
                f.write(clean_string + '\n')
                
                if (i + 1) % 1000 == 0:
                    print(f"   ✅ Written {i + 1} strings...")
        
        print(f"✅ Successfully wrote {len(entity_strings)} entity strings to {entity_file}")
        
        # Verify the file
        if entity_file.exists():
            file_size = entity_file.stat().st_size
            print(f"📄 File size: {file_size} bytes")
            
            # Try to read first few lines
            with open(entity_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📄 Total lines: {len(lines)}")
                if lines:
                    print(f"📄 First line: {lines[0].strip()}")
                    print(f"📄 Last line: {lines[-1].strip()}")
        
    except Exception as e:
        print(f"❌ Error writing entity strings: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    manual_fix_entities()


