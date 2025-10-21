#!/usr/bin/env python3
"""
Test script to verify chunking functionality works correctly
"""

import json
from typing import Dict, Any, List

def test_chunking_logic():
    """Test the chunking logic with sample data"""
    
    # Create sample large data similar to WHINT API response
    sample_data = {
        "data": [
            {
                "id": i,
                "name": f"Interface_{i}",
                "type": i % 22,  # Cycle through inventory types
                "description": f"Description for interface {i}",
                "sender_name": f"Sender_{i}",
                "receiver_name": f"Receiver_{i}"
            }
            for i in range(1000)  # Create 1000 items
        ]
    }
    
    # Convert to JSON to estimate size
    json_text = json.dumps(sample_data, indent=2)
    estimated_tokens = len(json_text) // 4
    
    print(f"Sample data size: {len(json_text):,} characters")
    print(f"Estimated tokens: {estimated_tokens:,}")
    
    # Test chunking parameters
    data_items = sample_data['data']
    total_items = len(data_items)
    chunk_size = max(10, min(100, total_items // 10))
    
    print(f"Total items: {total_items}")
    print(f"Chunk size: {chunk_size}")
    print(f"Number of chunks: {(total_items + chunk_size - 1) // chunk_size}")
    
    # Test chunk processing
    chunks = []
    for i in range(0, total_items, chunk_size):
        chunk = data_items[i:i + chunk_size]
        chunk_text = json.dumps(chunk, indent=2)
        chunk_tokens = len(chunk_text) // 4
        chunks.append({
            "start": i,
            "end": min(i + chunk_size, total_items),
            "size": len(chunk),
            "tokens": chunk_tokens
        })
    
    print("\nChunk breakdown:")
    for idx, chunk_info in enumerate(chunks):
        print(f"Chunk {idx + 1}: items {chunk_info['start']+1}-{chunk_info['end']} "
              f"({chunk_info['size']} items, ~{chunk_info['tokens']} tokens)")
    
    # Verify chunking doesn't exceed token limits
    max_chunk_tokens = max(chunk['tokens'] for chunk in chunks)
    print(f"\nLargest chunk: ~{max_chunk_tokens} tokens")
    print(f"Within 25k limit: {'✓' if max_chunk_tokens < 25000 else '✗'}")
    
    return True

if __name__ == "__main__":
    test_chunking_logic()