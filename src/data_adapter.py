"""
Data adapter to transform various JSON formats into the structure expected by Graph RAG.
This handles the transformation from your current JSON structure to the interface/sender/receiver format.
"""

from typing import Any, Dict, List, Optional
import json


def extract_metadata_value(metadata: List[Dict[str, Any]], key: str) -> Optional[str]:
    """Extract a value from metadata by name"""
    if not metadata:
        return None
    
    for item in metadata:
        if isinstance(item, dict) and item.get('name') == key:
            return item.get('value')
    return None


def extract_tag_values(tags: List[Dict[str, Any]], tag_name: str) -> List[str]:
    """Extract tag values by tag name"""
    if not tags:
        return []
    
    values = []
    for tag in tags:
        if isinstance(tag, dict):
            tag_obj = tag.get('tag', {})
            if isinstance(tag_obj, dict) and tag_obj.get('name') == tag_name:
                value = tag.get('value')
                if value:
                    values.append(value)
    return values


def transform_record_to_interface_format(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a record from your JSON format to the interface format expected by Graph RAG.
    
    Your format:
    {
        "type": "SAP_PO",
        "name": "Interface Name",
        "sender": {"name": "Sender System", "properties": [...]},
        "receiver": {"name": "Receiver System"},
        "metadata": [{"name": "Key", "value": "Value"}, ...],
        "tags": [{"value": "TagValue", "tag": {"name": "TagName"}}, ...]
    }
    
    Expected format:
    {
        "inv_name": "Interface Name",
        "sender": "Sender System",
        "receiver": "Receiver System", 
        "data_source": "Data Source",
        "type": "Interface Type",
        "properties": [...],
        "metadata": [...],
        "tags": [...]
    }
    """
    
    # Extract basic fields
    interface_name = record.get('name', '')
    interface_type = record.get('type', '')
    
    # Extract sender information
    sender_name = None
    sender_properties = []
    sender_obj = record.get('sender')
    if isinstance(sender_obj, dict):
        sender_name = sender_obj.get('name')
        sender_properties = sender_obj.get('properties', [])
    
    # Extract receiver information  
    receiver_name = None
    receiver_obj = record.get('receiver')
    if isinstance(receiver_obj, dict):
        receiver_name = receiver_obj.get('name')
    
    # Extract metadata
    metadata = record.get('metadata', [])
    
    # Extract tags
    tags = record.get('tags', [])
    
    # Determine data source from metadata or type
    data_source = extract_metadata_value(metadata, 'Adapter') or interface_type
    
    # Build the transformed record
    transformed = {
        'inv_name': interface_name,
        'sender': sender_name,
        'receiver': receiver_name,
        'data_source': data_source,
        'type': interface_type,
        'properties': sender_properties,
        'metadata': metadata,
        'tags': tags
    }
    
    # Add additional metadata fields as properties
    for meta_item in metadata:
        if isinstance(meta_item, dict):
            name = meta_item.get('name')
            value = meta_item.get('value')
            if name and value:
                # Add as a property for easier searching
                transformed[f'meta_{name.lower().replace(" ", "_")}'] = value
    
    return transformed


def adapt_data_for_graph_rag(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adapt a list of records to the format expected by Graph RAG.
    
    Args:
        data: List of records in your JSON format
        
    Returns:
        List of records in Graph RAG format
    """
    adapted_records = []
    
    for record in data:
        if isinstance(record, dict):
            try:
                adapted = transform_record_to_interface_format(record)
                adapted_records.append(adapted)
            except Exception as e:
                # Skip problematic records but log the issue
                print(f"Warning: Could not adapt record: {e}")
                continue
    
    return adapted_records


def analyze_data_structure(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the data structure to provide insights for Graph RAG.
    
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        'total_records': len(data),
        'records_with_sender': 0,
        'records_with_receiver': 0,
        'records_with_both': 0,
        'unique_senders': set(),
        'unique_receivers': set(),
        'unique_types': set(),
        'salesforce_mentions': 0,
        'sample_adaptations': []
    }
    
    for record in data[:10]:  # Analyze first 10 records
        if isinstance(record, dict):
            # Check for sender/receiver
            has_sender = 'sender' in record and record.get('sender')
            has_receiver = 'receiver' in record and record.get('receiver')
            
            if has_sender:
                analysis['records_with_sender'] += 1
                sender_obj = record.get('sender', {})
                if isinstance(sender_obj, dict):
                    sender_name = sender_obj.get('name')
                    if sender_name:
                        analysis['unique_senders'].add(sender_name)
            
            if has_receiver:
                analysis['records_with_receiver'] += 1
                receiver_obj = record.get('receiver', {})
                if isinstance(receiver_obj, dict):
                    receiver_name = receiver_obj.get('name')
                    if receiver_name:
                        analysis['unique_receivers'].add(receiver_name)
            
            if has_sender and has_receiver:
                analysis['records_with_both'] += 1
            
            # Check interface type
            interface_type = record.get('type')
            if interface_type:
                analysis['unique_types'].add(str(interface_type))
            
            # Check for Salesforce mentions
            record_str = json.dumps(record).lower()
            if 'salesforce' in record_str:
                analysis['salesforce_mentions'] += 1
            
            # Create sample adaptation
            try:
                adapted = transform_record_to_interface_format(record)
                analysis['sample_adaptations'].append({
                    'original': {k: v for k, v in record.items() if k in ['name', 'type', 'sender', 'receiver']},
                    'adapted': {k: v for k, v in adapted.items() if k in ['inv_name', 'sender', 'receiver', 'data_source', 'type']}
                })
            except Exception:
                pass
    
    # Convert sets to lists for JSON serialization
    analysis['unique_senders'] = list(analysis['unique_senders'])
    analysis['unique_receivers'] = list(analysis['unique_receivers'])
    analysis['unique_types'] = list(analysis['unique_types'])
    
    return analysis


if __name__ == "__main__":
    # Test the adapter
    import json
    
    with open('23-09-2025.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🔍 Data Structure Analysis")
    print("=" * 50)
    
    analysis = analyze_data_structure(data)
    print(f"Total records: {analysis['total_records']}")
    print(f"Records with sender: {analysis['records_with_sender']}")
    print(f"Records with receiver: {analysis['records_with_receiver']}")
    print(f"Records with both: {analysis['records_with_both']}")
    print(f"Salesforce mentions: {analysis['salesforce_mentions']}")
    print(f"Unique senders: {len(analysis['unique_senders'])}")
    print(f"Unique receivers: {len(analysis['unique_receivers'])}")
    print(f"Unique types: {len(analysis['unique_types'])}")
    
    print("\n📝 Sample Adaptations:")
    for i, sample in enumerate(analysis['sample_adaptations'][:3]):
        print(f"\nSample {i+1}:")
        print("Original:", json.dumps(sample['original'], indent=2))
        print("Adapted:", json.dumps(sample['adapted'], indent=2))

