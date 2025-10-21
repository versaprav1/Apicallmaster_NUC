#!/usr/bin/env python3
"""
Analyze JSON structure to understand sender/receiver data
"""

import json
import os

def analyze_json_structure():
    """Analyze the JSON file structure"""
    print("Analyzing JSON structure...")
    
    try:
        with open('23-09-2025.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Total records: {len(data)}")
        
        # Analyze first few records
        print("\nFirst record structure:")
        if data:
            first_record = data[0]
            print(f"Keys: {list(first_record.keys())}")
            
            # Look for sender/receiver in metadata
            if 'metadata' in first_record:
                print("\nMetadata items:")
                for item in first_record['metadata'][:10]:  # First 10 items
                    print(f"  {item.get('name', 'N/A')}: {item.get('value', 'N/A')}")
            
            # Look for sender/receiver in properties
            if 'properties' in first_record:
                print("\nProperties:")
                for prop in first_record['properties'][:10]:  # First 10 items
                    print(f"  {prop}")
        
        # Search for records with sender/receiver info
        print("\nSearching for sender/receiver information...")
        sender_receiver_records = []
        
        for i, record in enumerate(data[:100]):  # Check first 100 records
            record_str = json.dumps(record).lower()
            if 'sender' in record_str or 'receiver' in record_str:
                sender_receiver_records.append((i, record))
                if len(sender_receiver_records) >= 3:  # Get first 3 examples
                    break
        
        if sender_receiver_records:
            print(f"Found {len(sender_receiver_records)} records with sender/receiver info:")
            for i, (idx, record) in enumerate(sender_receiver_records):
                print(f"\nRecord {idx}:")
                print(f"  Name: {record.get('name', 'N/A')}")
                print(f"  Type: {record.get('type', 'N/A')}")
                
                # Check metadata for sender/receiver
                if 'metadata' in record:
                    for item in record['metadata']:
                        if 'sender' in item.get('name', '').lower() or 'receiver' in item.get('name', '').lower():
                            print(f"  {item['name']}: {item['value']}")
        else:
            print("No records found with explicit sender/receiver information")
            print("The data might use different field names or structure")
            
            # Show all unique metadata names
            all_metadata_names = set()
            for record in data[:50]:  # Check first 50 records
                if 'metadata' in record:
                    for item in record['metadata']:
                        all_metadata_names.add(item.get('name', ''))
            
            print(f"\nAll metadata names found (first 50 records):")
            for name in sorted(all_metadata_names):
                print(f"  - {name}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    analyze_json_structure()
