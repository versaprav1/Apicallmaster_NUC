#!/usr/bin/env python3
"""
Script to extract and list all interface names from the knowledge entities.
This provides the direct answer you wanted instead of a summary.
"""

import sys
from pathlib import Path
import re

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def extract_interface_names():
    """Extract all interface names from knowledge entities"""
    print("📋 Listing All Interface Names")
    print("=" * 50)
    
    ks = KnowledgeStore()
    
    # Get all entity files
    entity_files = list(ks.entity_store_dir.glob("*.jsonl"))
    
    if not entity_files:
        print("❌ No knowledge entity files found")
        return
    
    print(f"✅ Found {len(entity_files)} entity files:")
    for file in entity_files:
        print(f"   - {file.name}")
    
    all_names = set()  # Use set to avoid duplicates
    total_entities = 0
    
    for entity_file in entity_files:
        print(f"\n🔍 Processing {entity_file.name}...")
        
        try:
            with open(entity_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    total_entities += 1
                    
                    # Extract name field from entity string
                    # Look for patterns like "name:Interface Name" or "inv_name:Interface Name"
                    name_patterns = [
                        r'(?:^|[|]\s*)name:([^|]+?)(?:\s*[|]|$)',
                        r'(?:^|[|]\s*)inv_name:([^|]+?)(?:\s*[|]|$)'
                    ]
                    
                    for pattern in name_patterns:
                        matches = re.findall(pattern, line)
                        for match in matches:
                            name = match.strip()
                            if name and name != "n/a":
                                all_names.add(name)
                                
        except Exception as e:
            print(f"❌ Error processing {entity_file.name}: {str(e)}")
            continue
    
    print(f"\n📊 Summary:")
    print(f"   - Total entities processed: {total_entities}")
    print(f"   - Unique interface names found: {len(all_names)}")
    
    if not all_names:
        print("❌ No interface names found")
        return
    
    # Sort names for better readability
    sorted_names = sorted(all_names)
    
    print(f"\n📋 All Interface Names ({len(sorted_names)} total):")
    print("=" * 60)
    
    for i, name in enumerate(sorted_names, 1):
        print(f"{i:4d}. {name}")
        
        # Add pagination for very long lists
        if i % 100 == 0:
            response = input(f"\nShowing {i} of {len(sorted_names)} interfaces. Continue? (y/n/q to quit): ").lower()
            if response == 'n':
                break
            elif response == 'q':
                return
    
    print(f"\n✅ Listed {min(i, len(sorted_names))} interface names")
    
    # Offer to save to file
    save_response = input("\nSave complete list to file? (y/n): ").lower()
    if save_response == 'y':
        output_file = Path("interface_names_list.txt")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"All Interface Names ({len(sorted_names)} total)\n")
                f.write("=" * 50 + "\n\n")
                for i, name in enumerate(sorted_names, 1):
                    f.write(f"{i:4d}. {name}\n")
            print(f"✅ Saved to {output_file}")
        except Exception as e:
            print(f"❌ Error saving file: {str(e)}")

def extract_with_sender_receiver():
    """Extract interface names with sender/receiver information"""
    print("\n📋 Interface Names with Sender/Receiver Info")
    print("=" * 60)
    
    ks = KnowledgeStore()
    entity_files = list(ks.entity_store_dir.glob("*.jsonl"))
    
    interfaces_with_details = []
    
    for entity_file in entity_files:
        try:
            with open(entity_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Extract name
                    name_match = re.search(r'(?:^|[|]\s*)(?:inv_)?name:([^|]+?)(?:\s*[|]|$)', line)
                    if not name_match:
                        continue
                    
                    name = name_match.group(1).strip()
                    if not name or name == "n/a":
                        continue
                    
                    # Extract sender info
                    sender_patterns = [
                        r'(?:^|[|]\s*)(?:inv_)?sender_name:([^|]+?)(?:\s*[|]|$)',
                        r'(?:^|[|]\s*)sender_id:([^|]+?)(?:\s*[|]|$)'
                    ]
                    sender = "Unknown"
                    for pattern in sender_patterns:
                        sender_match = re.search(pattern, line)
                        if sender_match:
                            sender = sender_match.group(1).strip()
                            break
                    
                    # Extract receiver info
                    receiver_patterns = [
                        r'(?:^|[|]\s*)(?:inv_)?receiver_name:([^|]+?)(?:\s*[|]|$)',
                        r'(?:^|[|]\s*)receiver_id:([^|]+?)(?:\s*[|]|$)'
                    ]
                    receiver = "Unknown"
                    for pattern in receiver_patterns:
                        receiver_match = re.search(pattern, line)
                        if receiver_match:
                            receiver = receiver_match.group(1).strip()
                            break
                    
                    interfaces_with_details.append({
                        'name': name,
                        'sender': sender,
                        'receiver': receiver
                    })
                    
        except Exception as e:
            print(f"❌ Error processing {entity_file.name}: {str(e)}")
            continue
    
    # Remove duplicates based on name
    seen_names = set()
    unique_interfaces = []
    for interface in interfaces_with_details:
        if interface['name'] not in seen_names:
            seen_names.add(interface['name'])
            unique_interfaces.append(interface)
    
    print(f"✅ Found {len(unique_interfaces)} unique interfaces with sender/receiver info")
    
    # Show first 20 as sample
    print(f"\nSample (first 20 interfaces):")
    print("-" * 100)
    print(f"{'#':>3} {'Interface Name':<40} {'Sender':<20} {'Receiver':<20}")
    print("-" * 100)
    
    for i, interface in enumerate(unique_interfaces[:20], 1):
        name = interface['name'][:38] + "..." if len(interface['name']) > 38 else interface['name']
        sender = interface['sender'][:18] + "..." if len(interface['sender']) > 18 else interface['sender']
        receiver = interface['receiver'][:18] + "..." if len(interface['receiver']) > 18 else interface['receiver']
        
        print(f"{i:>3} {name:<40} {sender:<20} {receiver:<20}")
    
    if len(unique_interfaces) > 20:
        print(f"\n... and {len(unique_interfaces) - 20} more interfaces")
    
    # Offer to save detailed list
    save_response = input(f"\nSave complete detailed list to file? (y/n): ").lower()
    if save_response == 'y':
        output_file = Path("interfaces_with_details.csv")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Interface Name,Sender,Receiver\n")
                for interface in unique_interfaces:
                    f.write(f'"{interface["name"]}","{interface["sender"]}","{interface["receiver"]}"\n')
            print(f"✅ Saved to {output_file}")
        except Exception as e:
            print(f"❌ Error saving file: {str(e)}")

if __name__ == "__main__":
    print("Choose an option:")
    print("1. List interface names only")
    print("2. List interfaces with sender/receiver details")
    print("3. Both")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        extract_interface_names()
    
    if choice in ['2', '3']:
        extract_with_sender_receiver()


