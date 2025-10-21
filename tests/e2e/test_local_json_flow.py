#!/usr/bin/env python3
"""
Test script to demonstrate the Local JSON File flow in the WHINT API AI Assistant.
This shows what happens when a user selects "Local JSON File" as the data source.
"""

import json
import os
from pathlib import Path

def test_local_json_flow():
    """Test the complete flow when Local JSON File is selected"""
    
    print("🔍 Testing Local JSON File Flow")
    print("=" * 50)
    
    # Step 1: Check if the JSON file exists
    json_file = Path("23-09-2025.json")
    print(f"1. Checking JSON file: {json_file.resolve()}")
    
    if not json_file.exists():
        print(f"   ❌ File not found: {json_file}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Files in current directory:")
        for f in os.listdir("."):
            if f.endswith(".json"):
                print(f"     - {f}")
        return
    
    print(f"   ✅ File exists: {json_file.resolve()}")
    
    # Step 2: Load and analyze the JSON data
    print(f"\n2. Loading JSON data...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"   ✅ Successfully loaded JSON data")
        print(f"   📊 Data type: {type(data)}")
        
        if isinstance(data, list):
            print(f"   📊 Number of records: {len(data)}")
            if len(data) > 0:
                print(f"   📊 Sample record keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
        elif isinstance(data, dict):
            print(f"   📊 Dictionary keys: {list(data.keys())}")
            
    except Exception as e:
        print(f"   ❌ Error loading JSON: {str(e)}")
        return
    
    # Step 3: Test seed extraction
    print(f"\n3. Testing seed extraction...")
    from methods.graph_rag import _extract_names_from_query
    
    test_queries = [
        "which systems send data to salesforce",
        "what is the shortest path from SAP to Azure",
        "find interfaces connected to MuleSoft",
        "show me all Oracle systems"
    ]
    
    for query in test_queries:
        seeds = _extract_names_from_query(query)
        print(f"   Query: '{query}'")
        print(f"   Seeds: {seeds}")
    
    # Step 4: Simulate the Graph RAG flow (without Neo4j)
    print(f"\n4. Simulating Graph RAG flow...")
    print(f"   📝 Query: 'which systems send data to salesforce'")
    print(f"   📊 Data provided: {len(data) if isinstance(data, list) else 'Not a list'}")
    print(f"   🔍 Seeds extracted: {_extract_names_from_query('which systems send data to salesforce')}")
    
    # Step 5: Show what would happen in the app
    print(f"\n5. What happens in the Streamlit app:")
    print(f"   a) User selects 'Local JSON File' as data source")
    print(f"   b) App loads JSON data from: {json_file.resolve()}")
    print(f"   c) User asks: 'which systems send data to salesforce'")
    print(f"   d) Method router selects 'graph_rag' method")
    print(f"   e) Graph RAG receives {len(data) if isinstance(data, list) else 'N/A'} records")
    print(f"   f) Graph RAG tries to ingest data into Neo4j")
    print(f"   g) Graph RAG searches for 'Salesforce' in the graph")
    print(f"   h) Graph RAG returns results or error")
    
    # Step 6: Check for potential issues
    print(f"\n6. Potential issues to check:")
    
    # Check if data has the expected structure
    if isinstance(data, list) and len(data) > 0:
        sample_record = data[0]
        if isinstance(sample_record, dict):
            expected_keys = ['inv_name', 'sender', 'receiver', 'data_source']
            missing_keys = [key for key in expected_keys if key not in sample_record]
            if missing_keys:
                print(f"   ⚠️ Missing expected keys: {missing_keys}")
            else:
                print(f"   ✅ Data structure looks good")
                
            # Check for Salesforce-related data
            salesforce_records = []
            for record in data[:100]:  # Check first 100 records
                if isinstance(record, dict):
                    for key, value in record.items():
                        if isinstance(value, str) and 'salesforce' in value.lower():
                            salesforce_records.append(record)
                            break
            
            print(f"   📊 Records mentioning 'salesforce': {len(salesforce_records)}")
            if salesforce_records:
                print(f"   📝 Sample Salesforce record keys: {list(salesforce_records[0].keys())}")
    
    print(f"\n✅ Local JSON File flow test completed!")

if __name__ == "__main__":
    test_local_json_flow()

