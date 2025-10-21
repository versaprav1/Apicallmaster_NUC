#!/usr/bin/env python3
"""
Simple script to extract all interface names and save to file.
This answers your "list all interfaces" question directly.
"""

import sys
from pathlib import Path
import re

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from knowledge_store import KnowledgeStore

def get_all_interface_names():
    """Extract all interface names and save to file"""
    print("📋 Extracting All Interface Names")
    print("=" * 50)
    
    ks = KnowledgeStore()
    entity_files = list(ks.entity_store_dir.glob("*.jsonl"))
    
    if not entity_files:
        print("❌ No knowledge entity files found")
        return
    
    all_names = set()
    total_entities = 0
    
    for entity_file in entity_files:
        print(f"Processing {entity_file.name}...")
        
        try:
            with open(entity_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    total_entities += 1
                    
                    # Extract name field from entity string
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
    
    # Sort names
    sorted_names = sorted(all_names)
    
    print(f"\n📊 Results:")
    print(f"   - Total entities processed: {total_entities}")
    print(f"   - Unique interface names found: {len(sorted_names)}")
    
    # Save to file
    output_file = Path("all_interface_names.txt")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"All Interface Names ({len(sorted_names)} total)\n")
            f.write("Generated from WHINT API knowledge entities\n")
            f.write("=" * 60 + "\n\n")
            for i, name in enumerate(sorted_names, 1):
                f.write(f"{i:4d}. {name}\n")
        
        print(f"✅ Saved complete list to {output_file}")
        
        # Show first 10 as preview
        print(f"\nPreview (first 10 interfaces):")
        for i, name in enumerate(sorted_names[:10], 1):
            print(f"  {i:2d}. {name}")
        
        if len(sorted_names) > 10:
            print(f"  ... and {len(sorted_names) - 10} more")
            
    except Exception as e:
        print(f"❌ Error saving file: {str(e)}")

if __name__ == "__main__":
    get_all_interface_names()


