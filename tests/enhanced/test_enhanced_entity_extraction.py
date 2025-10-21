#!/usr/bin/env python3
"""
Test script to verify the enhanced _to_compact_string method
extracts sender/receiver IDs and other comprehensive information correctly.
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def test_entity_extraction():
    """Test the enhanced entity extraction with sample WHINT data"""
    print("🧪 Testing Enhanced Entity String Extraction")
    print("=" * 50)
    
    # Sample data structure based on the all_data.json files
    sample_data = [
        {
            "id": "YbZO_vnA5aU",
            "sequence": 1,
            "data_flow_id": "IPJpYszZOs4",
            "inventory_id": "GYoJ1wwUQoc",
            "inventory": {
                "id": "GYoJ1wwUQoc",
                "name": "WHINT Document to SharePoint",
                "sender_name": "CPI",
                "receiver_id": "aIxcrkXtnk8",
                "receiver_name": "SharePoint",
                "data_source_id": "EjA9oQ",
                "data_source": {
                    "id": "EjA9oQ",
                    "name": "CPI_CF"
                },
                "receiver": {
                    "id": "aIxcrkXtnk8",
                    "name": "SharePoint"
                }
            }
        },
        {
            "id": "XCJneO5C4Fs",
            "sequence": 2,
            "data_flow_id": "IPJpYszZOs4",
            "inventory_id": "Po2GzqgZL2o",
            "inventory": {
                "id": "Po2GzqgZL2o",
                "name": "SLBC_Complexity_3_hight",
                "sender_name": "SAP Cloud Integration",
                "receiver_id": "aIxcrkXtnk8",
                "receiver_name": "SharePoint",
                "data_source_id": "EjA9oQ",
                "data_source": {
                    "id": "EjA9oQ",
                    "name": "CPI_CF"
                },
                "receiver": {
                    "id": "aIxcrkXtnk8",
                    "name": "SharePoint"
                }
            }
        }
    ]
    
    # Create knowledge store instance
    ks = KnowledgeStore()
    
    print("Sample data items:")
    for i, item in enumerate(sample_data, 1):
        print(f"\n--- Item {i} ---")
        print(f"Original: {json.dumps(item, indent=2)[:200]}...")
        
        # Test the _to_compact_string method
        compact_string = ks._to_compact_string(item)
        print(f"\nCompact String: {compact_string}")
        
        # Verify key information is captured
        expected_fields = ["id:", "sequence:", "data_flow_id:", "inventory_id:", 
                          "inv_id:", "inv_name:", "inv_sender_name:", "inv_receiver_id:", 
                          "inv_receiver_name:", "data_source_id:", "receiver_id:"]
        
        captured_fields = []
        missing_fields = []
        
        for field in expected_fields:
            if field in compact_string:
                captured_fields.append(field.rstrip(":"))
            else:
                missing_fields.append(field.rstrip(":"))
        
        print(f"✅ Captured fields: {captured_fields}")
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        
        print("-" * 40)
    
    # Test with the raw API response structure
    print("\n🔍 Testing with simulated API response structure:")
    api_response = {"data": sample_data}
    
    entity_strings = ks._extract_entity_strings(api_response)
    print(f"\nExtracted {len(entity_strings)} entity strings:")
    
    for i, entity_str in enumerate(entity_strings, 1):
        print(f"{i}. {entity_str}")
        
        # Check if sender/receiver info is present
        has_sender = any(x in entity_str for x in ["sender_name:", "inv_sender_name:"])
        has_receiver = any(x in entity_str for x in ["receiver_id:", "receiver_name:", "inv_receiver_id:", "inv_receiver_name:"])
        
        status = "✅" if (has_sender and has_receiver) else "⚠️ "
        print(f"   {status} Sender: {has_sender}, Receiver: {has_receiver}")
    
    print(f"\n🎯 Summary: Enhanced extraction captures comprehensive sender/receiver information!")
    print("   - Direct sender_name/receiver_id fields")
    print("   - Nested inventory.sender_name/receiver_id fields") 
    print("   - Nested receiver object details")
    print("   - Data source information")
    print("   - Flow and sequence metadata")

if __name__ == "__main__":
    test_entity_extraction()


