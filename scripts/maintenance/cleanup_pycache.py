#!/usr/bin/env python3
"""
Script to clean up __pycache__ directories recursively.
Run this before starting the Streamlit app to avoid file watcher issues.
"""

import os
import shutil
import sys
from pathlib import Path


def remove_pycache_dirs(root_path: str = ".") -> int:
    """
    Recursively find and remove all __pycache__ directories.
    
    Args:
        root_path: Root directory to search from (default: current directory)
        
    Returns:
        Number of __pycache__ directories removed
    """
    removed_count = 0
    root = Path(root_path).resolve()
    
    print(f"🔍 Searching for __pycache__ directories in: {root}")
    print("-" * 60)
    
    # Find all __pycache__ directories
    for pycache_dir in root.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                # Count files before removal
                file_count = len(list(pycache_dir.rglob("*")))
                
                # Remove the directory
                shutil.rmtree(pycache_dir)
                removed_count += 1
                
                # Show relative path from root
                rel_path = pycache_dir.relative_to(root)
                print(f"✅ Removed: {rel_path} ({file_count} files)")
                
            except Exception as e:
                rel_path = pycache_dir.relative_to(root)
                print(f"❌ Failed to remove: {rel_path} - {e}")
    
    print("-" * 60)
    print(f"📊 Summary: Removed {removed_count} __pycache__ directories")
    
    return removed_count


def main():
    """Main function to handle command line arguments and execute cleanup."""
    
    # Default to current directory
    target_path = "."
    
    # Check for command line argument
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        if not os.path.exists(target_path):
            print(f"❌ Error: Path '{target_path}' does not exist")
            sys.exit(1)
    
    print("🧹 Python __pycache__ Cleanup Script")
    print("=" * 60)
    
    try:
        removed_count = remove_pycache_dirs(target_path)
        
        if removed_count == 0:
            print("✨ No __pycache__ directories found - already clean!")
        else:
            print(f"🎉 Cleanup complete! Removed {removed_count} __pycache__ directories")
            print("\n💡 Tip: Run this script before starting Streamlit to avoid file watcher issues")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
