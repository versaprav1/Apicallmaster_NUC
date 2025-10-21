#!/usr/bin/env python3
"""
Script to extract comprehensive entity strings directly from all_data.json files.
This processes the raw data files to create knowledge entities with sender/receiver information.
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def extract_from_all_data():
    """Extract entity strings from all_data.json files"""
    print("📁 Extracting Entities from all_data.json Files")
    print("=" * 50)
    
    # Look for all_data files in assets/attached_assets
    assets_dir = Path("assets/attached_assets")
    if not assets_dir.exists():
        print(f"❌ Assets directory not found: {assets_dir}")
        return
    
    # Find all_data files
    all_data_files = list(assets_dir.glob("all_data*.json"))
    
    if not all_data_files:
        print(f"❌ No all_data*.json files found in {assets_dir}")
        return
    
    print(f"✅ Found {len(all_data_files)} all_data files:")
    for file in all_data_files:
        print(f"   - {file.name}")
    
    ks = KnowledgeStore()
    
    for data_file in all_data_files:
        print(f"\n🔍 Processing {data_file.name}...")
        
        try:
            # Load the data file
            print("Loading JSON data...")
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ Loaded JSON with {len(data) if isinstance(data, list) else 'unknown'} items")
            
            # Process the data structure
            all_items = []
            
            if isinstance(data, list):
                # Process each top-level item
                for item in data:
                    if isinstance(item, dict):
                        # Add the item itself
                        all_items.append(item)
                        
                        # Process nested items if present
                        if "items" in item and isinstance(item["items"], list):
                            for sub_item in item["items"]:
                                if isinstance(sub_item, dict):
                                    all_items.append(sub_item)
            else:
                print(f"⚠️  Unexpected data structure: {type(data)}")
                continue
            
            print(f"✅ Found {len(all_items)} total items to process")
            
            # Extract entity strings using enhanced method
            print("Extracting entity strings with enhanced method...")
            entity_strings = []
            
            for item in all_items[:1000]:  # Limit to avoid overwhelming
                try:
                    entity_str = ks._to_compact_string(item)
                    if entity_str:
                        entity_strings.append(entity_str)
                except Exception as e:
                    print(f"⚠️  Error processing item: {str(e)}")
                    continue
            
            print(f"✅ Extracted {len(entity_strings)} entity strings")
            
            # Show samples with sender/receiver analysis
            print("\n📊 Sample Analysis:")
            sender_count = 0
            receiver_count = 0
            both_count = 0
            
            for i, entity_str in enumerate(entity_strings[:5]):
                has_sender = any(x in entity_str for x in ["sender_name:", "inv_sender_name:", "sender_id:"])
                has_receiver = any(x in entity_str for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"])
                
                if has_sender:
                    sender_count += 1
                if has_receiver:
                    receiver_count += 1
                if has_sender and has_receiver:
                    both_count += 1
                
                status = "✅" if (has_sender and has_receiver) else "⚠️ "
                print(f"   {i+1}. {status} {entity_str[:100]}...")
                print(f"      Sender: {has_sender}, Receiver: {has_receiver}")
            
            # Overall statistics
            total_with_sender = sum(1 for e in entity_strings if any(x in e for x in ["sender_name:", "inv_sender_name:", "sender_id:"]))
            total_with_receiver = sum(1 for e in entity_strings if any(x in e for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"]))
            total_with_both = sum(1 for e in entity_strings if any(x in e for x in ["sender_name:", "inv_sender_name:", "sender_id:"]) and any(x in e for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"]))
            
            print(f"\n📈 Statistics for {data_file.name}:")
            print(f"   - Total entities: {len(entity_strings)}")
            print(f"   - With sender info: {total_with_sender} ({total_with_sender/len(entity_strings)*100:.1f}%)")
            print(f"   - With receiver info: {total_with_receiver} ({total_with_receiver/len(entity_strings)*100:.1f}%)")
            print(f"   - With both: {total_with_both} ({total_with_both/len(entity_strings)*100:.1f}%)")
            
            # Save to persistent store with a custom endpoint name based on file
            endpoint_name = f"file_import_{data_file.stem}"
            print(f"\n💾 Saving to persistent store as endpoint: {endpoint_name}")
            
            new_count = ks.append_entity_strings_persistent(endpoint_name, entity_strings)
            print(f"✅ Added {new_count} new entity strings to persistent store")
            
            # Show file location
            entity_file_path = ks._entity_store_path(endpoint_name)
            print(f"📁 Saved to: {entity_file_path}")
            
        except Exception as e:
            print(f"❌ Error processing {data_file.name}: {str(e)}")
            continue
    
    print(f"\n🎯 Extraction Complete!")
    print(f"   Enhanced entity strings with sender/receiver IDs are now available.")
    print(f"   When you ask questions, the LLM can access this rich metadata.")

if __name__ == "__main__":
    extract_from_all_data()


