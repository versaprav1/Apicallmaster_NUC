#!/usr/bin/env python3
"""
Backfill script to reprocess existing cache entries with enhanced entity extraction.
This will extract comprehensive sender/receiver information from cached API responses
and update the persistent knowledge_entities files.
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def backfill_enhanced_entities():
    """Reprocess existing cache entries with enhanced entity extraction"""
    print("🔄 Backfilling Enhanced Entity Strings")
    print("=" * 50)
    
    ks = KnowledgeStore()
    
    # Load all valid cache entries
    print("Loading existing cache entries...")
    cache_entries = ks.get_all_valid_entries(limit=None)  # Get all entries
    
    if not cache_entries:
        print("❌ No valid cache entries found to process")
        return
    
    print(f"✅ Found {len(cache_entries)} valid cache entries")
    
    total_entities_added = 0
    processed_endpoints = set()
    
    for i, entry in enumerate(cache_entries, 1):
        print(f"\n--- Processing entry {i}/{len(cache_entries)} ---")
        endpoint = entry.get('endpoint', 'unknown')
        cache_key = entry.get('cache_key', 'unknown')
        
        print(f"Endpoint: {endpoint}")
        print(f"Cache Key: {cache_key[:20]}...")
        
        # Load the full cache entry
        try:
            cache_file = ks.cache_dir / f"{cache_key}.json"
            if not cache_file.exists():
                print(f"⚠️  Cache file not found: {cache_file}")
                continue
                
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            raw_response = cached_data.get('raw_response')
            if not raw_response:
                print(f"⚠️  No raw_response found in cache entry")
                continue
            
            # Extract entity strings with enhanced method
            print("Extracting enhanced entity strings...")
            entity_strings = ks._extract_entity_strings(raw_response)
            
            if not entity_strings:
                print(f"⚠️  No entity strings extracted")
                continue
            
            print(f"✅ Extracted {len(entity_strings)} entity strings")
            
            # Show sample of extracted data
            if entity_strings:
                sample_entity = entity_strings[0]
                has_sender = any(x in sample_entity for x in ["sender_name:", "inv_sender_name:"])
                has_receiver = any(x in sample_entity for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"])
                
                print(f"Sample entity: {sample_entity[:100]}...")
                print(f"Contains sender info: {has_sender}")
                print(f"Contains receiver info: {has_receiver}")
            
            # Append to persistent store
            new_count = ks.append_entity_strings_persistent(endpoint, entity_strings)
            total_entities_added += new_count
            processed_endpoints.add(endpoint)
            
            print(f"✅ Added {new_count} new entity strings to persistent store")
            
        except Exception as e:
            print(f"❌ Error processing cache entry {cache_key}: {str(e)}")
            continue
    
    print(f"\n🎯 Backfill Summary:")
    print(f"   - Processed {len(cache_entries)} cache entries")
    print(f"   - Updated {len(processed_endpoints)} unique endpoints")
    print(f"   - Added {total_entities_added} new entity strings total")
    
    # Show current state of persistent stores
    print(f"\n📂 Current Persistent Entity Stores:")
    for endpoint in processed_endpoints:
        try:
            entity_count = len(ks.load_entity_strings_persistent(endpoint))
            print(f"   - {endpoint}: {entity_count} entities")
            
            # Show sample entities with enhanced info
            sample_entities = ks.load_entity_strings_persistent(endpoint, limit=2)
            for j, entity in enumerate(sample_entities, 1):
                has_sender = any(x in entity for x in ["sender_name:", "inv_sender_name:"])
                has_receiver = any(x in entity for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"])
                status = "✅" if (has_sender and has_receiver) else "⚠️ "
                print(f"     {j}. {status} {entity[:80]}...")
        except Exception as e:
            print(f"     ❌ Error reading {endpoint}: {str(e)}")
    
    if total_entities_added > 0:
        print(f"\n🚀 Success! Enhanced entity extraction is now active.")
        print(f"   Next time you ask questions, the LLM will have access to:")
        print(f"   - Sender/Receiver IDs and names")
        print(f"   - Data source information") 
        print(f"   - Flow and inventory metadata")
        print(f"   - E2E monitoring fields (if present)")
    else:
        print(f"\n💡 No new entities were added. This might mean:")
        print(f"   - Entities were already processed with enhanced extraction")
        print(f"   - Cache entries don't contain the expected data structure")
        print(f"   - All extracted entities were duplicates")

if __name__ == "__main__":
    backfill_enhanced_entities()


