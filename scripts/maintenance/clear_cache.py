#!/usr/bin/env python3
"""
Script to clear the knowledge cache to force fresh API calls and entity string extraction.
"""

import os
import shutil
import json
from pathlib import Path

def clear_knowledge_cache():
    """Clear all knowledge cache files."""
    
    print("🧹 Clearing Knowledge Cache")
    print("=" * 40)
    
    cache_dir = Path("knowledge_cache")
    entities_dir = Path("knowledge_entities")
    
    if cache_dir.exists():
        # Count files before deletion
        cache_files = list(cache_dir.glob("*.json"))
        print(f"📊 Found {len(cache_files)} cache files:")
        for file in cache_files:
            print(f"   - {file.name}")
        
        # Remove all cache files
        for file in cache_files:
            try:
                file.unlink()
                print(f"   ✅ Deleted: {file.name}")
            except Exception as e:
                print(f"   ❌ Failed to delete {file.name}: {e}")
        
        print(f"\n🎉 Cleared {len(cache_files)} cache files")
    else:
        print("📁 No cache directory found")
    
    if entities_dir.exists():
        # Count entity files
        entity_files = list(entities_dir.glob("*.jsonl"))
        if entity_files:
            print(f"\n📄 Found {len(entity_files)} entity files:")
            for file in entity_files:
                print(f"   - {file.name}")
            
            # Ask before deleting entity files (they're persistent)
            response = input(f"\n❓ Delete {len(entity_files)} persistent entity files? (y/N): ").strip().lower()
            if response == 'y':
                for file in entity_files:
                    try:
                        file.unlink()
                        print(f"   ✅ Deleted: {file.name}")
                    except Exception as e:
                        print(f"   ❌ Failed to delete {file.name}: {e}")
            else:
                print("   ⏭️  Keeping entity files")
        else:
            print(f"\n📄 No entity files found in {entities_dir}")
    else:
        print(f"\n📁 No entities directory found")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Start Streamlit: streamlit run app.py")
    print(f"   2. Ask a new question to trigger fresh API calls")
    print(f"   3. Entity strings will be extracted and saved")

if __name__ == "__main__":
    clear_knowledge_cache()
