#!/usr/bin/env python3
"""
Final fix to create the entity strings file with the correct name.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_store import KnowledgeStore

def final_fix():
    """Create the entity strings file with the correct name."""
    
    print("🔧 Final Fix - Creating Entity Strings File")
    print("=" * 50)
    
    # Initialize knowledge store
    ks = KnowledgeStore()
    
    # Get the cache entry
    entries = ks.get_all_valid_entries()
    
    if not entries:
        print("❌ No cache entries found")
        return
    
    entry = entries[0]  # Get first entry
    entity_strings = entry.get('entity_strings', [])
    endpoint = entry.get('endpoint', 'unknown')
    
    print(f"📊 Found {len(entity_strings)} entity strings")
    print(f"📄 Endpoint: {endpoint}")
    
    # Get the correct file path (with fixed endpoint key)
    entity_file = ks._entity_store_path(endpoint)
    print(f"📄 Target file: {entity_file}")
    
    # Delete any existing wrong files
    wrong_files = [
        "knowledge_entities/https_whint.prod.apimanagement.eu10.hana.ondemand.com",
        "knowledge_entities/https_whint.prod.apimanagement.eu10.hana.ondemand.com:443_wic_interfaces.jsonl"
    ]
    
    for wrong_file in wrong_files:
        if os.path.exists(wrong_file):
            os.remove(wrong_file)
            print(f"🗑️  Deleted wrong file: {wrong_file}")
    
    # Write entity strings to the correct file
    try:
        with open(entity_file, 'w', encoding='utf-8') as f:
            for i, entity_string in enumerate(entity_strings):
                # Clean the string and write it
                clean_string = str(entity_string).replace('\n', ' ').replace('\r', ' ')
                f.write(clean_string + '\n')
                
                if (i + 1) % 1000 == 0:
                    print(f"   ✅ Written {i + 1} strings...")
        
        print(f"✅ Successfully wrote {len(entity_strings)} entity strings")
        
        # Verify the file
        if entity_file.exists():
            file_size = entity_file.stat().st_size
            print(f"📄 File size: {file_size} bytes")
            
            # Read first few lines
            with open(entity_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📄 Total lines: {len(lines)}")
                if lines:
                    print(f"📄 First line: {lines[0].strip()}")
                    print(f"📄 Last line: {lines[-1].strip()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_fix()


