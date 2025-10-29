#!/usr/bin/env python3
"""
Live Data Synchronization Script

This script:
1. Fetches live data from WHINT API (with pagination)
2. Stores it as timestamped JSON file
3. Updates DuckDB database
4. Updates Neo4j graph database

Usage:
    python live_data_sync.py --full          # Full sync (all data)
    python live_data_sync.py --incremental   # Incremental sync (new data only)
    python live_data_sync.py --update-all    # Update all storage systems from existing JSON
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import duckdb
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.graph_store_neo4j import Neo4jGraphStore

# Load environment variables
load_dotenv()


class LiveDataSync:
    """Synchronize live API data to all storage systems"""
    
    def __init__(self, api_url: str = None, api_key: str = None, username: str = None, password: str = None):
        """Initialize with API credentials"""
        self.api_url = api_url or os.getenv('WHINT_API_BASE_URL')
        self.api_key = api_key or os.getenv('WHINT_API_X_API_KEY')
        self.username = username or os.getenv('WHINT_USERNAME')
        self.password = password or os.getenv('WHINT_PASSWORD')
        
        if not all([self.api_url, self.api_key]):
            raise ValueError("Missing API credentials. Set WHINT_API_BASE_URL and WHINT_API_X_API_KEY in .env")
        
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        })
        
        # Get bearer token if username/password provided
        if self.username and self.password:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get bearer token"""
        print("🔐 Authenticating with WHINT API...")
        auth_url = self.api_url.replace('/inventory/query', '/login')
        
        try:
            response = self.session.post(
                auth_url,
                json={'username': self.username, 'password': self.password}
            )
            response.raise_for_status()
            token = response.json().get('token') or response.json().get('access_token')
            
            if token:
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                print("✅ Authentication successful")
            else:
                print("⚠️ No token received, continuing with API key only")
        except Exception as e:
            print(f"⚠️ Authentication failed: {str(e)}")
            print("Continuing with API key only")
    
    def fetch_live_data(self, limit_per_page: int = 5000, max_records: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all data from WHINT API with pagination
        
        Args:
            limit_per_page: Number of records per API call
            max_records: Maximum total records to fetch (None = all)
        
        Returns:
            List of interface records
        """
        print("📡 Fetching live data from WHINT API...")
        print(f"   API URL: {self.api_url}")
        
        all_results = []
        seen_ids = set()
        offset = 0
        page_num = 0
        
        while True:
            page_num += 1
            
            # Build query
            query = {
                "query": {
                    "entity": "inventory",
                    "limit": limit_per_page,
                    "offset": offset
                }
            }
            
            try:
                print(f"   Fetching page {page_num} (offset: {offset}, limit: {limit_per_page})...", end=" ")
                response = self.session.post(self.api_url, json=query)
                response.raise_for_status()
                
                data = response.json()
                page = data.get("data", []) if isinstance(data, dict) else data
                
                if not page:
                    print("No more data")
                    break
                
                # Deduplicate by ID
                new_count = 0
                for item in page:
                    if isinstance(item, dict) and "id" in item:
                        if item["id"] not in seen_ids:
                            all_results.append(item)
                            seen_ids.add(item["id"])
                            new_count += 1
                    else:
                        all_results.append(item)
                        new_count += 1
                
                print(f"Got {len(page)} records ({new_count} new)")
                
                # Check if we've reached the end or max_records
                if len(page) < limit_per_page:
                    break
                
                if max_records and len(all_results) >= max_records:
                    print(f"   Reached max_records limit: {max_records}")
                    all_results = all_results[:max_records]
                    break
                
                offset += limit_per_page
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                break
        
        print(f"✅ Fetched {len(all_results)} total records")
        return all_results
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Save data to timestamped JSON file
        
        Args:
            data: List of interface records
            filename: Custom filename (default: auto-generated with timestamp)
        
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
            filename = f"api_data_{timestamp}.json"
        
        print(f"💾 Saving to JSON: {filename}...")
        
        # Save main file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Also save metadata
        metadata = {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "record_count": len(data),
            "source": "WHINT API Live Fetch",
            "api_url": self.api_url
        }
        
        metadata_file = filename.replace('.json', '_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        file_size_mb = Path(filename).stat().st_size / (1024 * 1024)
        print(f"✅ Saved {len(data)} records to {filename} ({file_size_mb:.2f} MB)")
        print(f"   Metadata: {metadata_file}")
        
        return filename
    
    def update_duckdb(self, json_file: str, db_path: str = "duckdb_engine/wic.duckdb") -> bool:
        """
        Update DuckDB database from JSON file
        
        Args:
            json_file: Path to JSON file
            db_path: Path to DuckDB database
        
        Returns:
            True if successful
        """
        print(f"\n🦆 Updating DuckDB: {db_path}...")
        
        try:
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to DuckDB
            con = duckdb.connect(str(db_path))
            con.execute("PRAGMA threads=4")
            
            # Drop old table
            print("   Dropping old table...")
            con.execute("DROP TABLE IF EXISTS raw_all")
            
            # Load JSON data
            print(f"   Loading data from {json_file}...")
            con.execute(
                "CREATE TABLE raw_all AS SELECT * FROM read_json_auto(?, maximum_object_size=268435456)",
                [str(json_file)],
            )
            
            # Get count
            total = con.execute("SELECT COUNT(*) FROM raw_all").fetchone()[0]
            print(f"   Loaded {total} rows")
            
            # Create normalized view
            print("   Creating inventory_view...")
            con.execute("DROP VIEW IF EXISTS inventory_view")
            con.execute("""
                CREATE VIEW inventory_view AS
                SELECT 
                    r.name AS norm_name,
                    r.type AS norm_type,
                    r.description AS norm_description,
                    r.sender->>'name' AS norm_sender_name,
                    r.receiver->>'name' AS norm_receiver_name,
                    r.metadata,
                    r.properties,
                    r.tags,
                    r.sender,
                    r.receiver
                FROM raw_all AS r
            """)
            
            # Show type distribution
            try:
                dist = con.execute(
                    "SELECT CAST(norm_type AS VARCHAR) AS type_id, COUNT(*) AS cnt FROM inventory_view GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
                ).fetchall()
                print("   Type distribution (top 10):")
                for row in dist:
                    print(f"      {row[0]}: {row[1]}")
            except Exception as e:
                print(f"   Could not compute type distribution: {e}")
            
            con.close()
            print(f"✅ DuckDB updated successfully: {total} records")
            return True
            
        except Exception as e:
            print(f"❌ DuckDB update failed: {str(e)}")
            return False
    
    def update_neo4j(self, json_file: str) -> bool:
        """
        Update Neo4j graph database from JSON file
        
        Args:
            json_file: Path to JSON file
        
        Returns:
            True if successful
        """
        print(f"\n🕸️  Updating Neo4j Graph Database...")
        
        # Check Neo4j credentials
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            print("⚠️  Neo4j credentials not found in .env")
            print("   Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
            print("   Skipping Neo4j update")
            return False
        
        try:
            # Load JSON data
            print(f"   Loading data from {json_file}...")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"   Loaded {len(data)} records")
            
            # Transform data for Neo4j
            print("   Transforming data for Neo4j...")
            transformed_data = self._transform_for_neo4j(data)
            
            # Connect to Neo4j
            print(f"   Connecting to Neo4j: {neo4j_uri}")
            store = Neo4jGraphStore(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            # Clear existing data
            print("   Clearing existing data...")
            store.run_tx("MATCH (n) DETACH DELETE n")
            
            # Set up constraints
            print("   Setting up constraints...")
            store.ensure_constraints()
            
            # Bulk upsert
            print("   Starting bulk upsert...")
            store.bulk_upsert(transformed_data)
            
            # Verify ingestion
            print("   Verifying ingestion...")
            result = store.run_tx("MATCH (n) RETURN count(n) as total")
            total_nodes = result[0]['total'] if result else 0
            
            result = store.run_tx("MATCH ()-[r:SENT_BY]->() RETURN count(r) as count")
            sent_count = result[0]['count'] if result else 0
            
            result = store.run_tx("MATCH ()-[r:RECEIVED_BY]->() RETURN count(r) as count")
            received_count = result[0]['count'] if result else 0
            
            print(f"\n✅ Neo4j updated successfully!")
            print(f"   Total nodes: {total_nodes}")
            print(f"   SENT_BY relationships: {sent_count}")
            print(f"   RECEIVED_BY relationships: {received_count}")
            
            store.close()
            return True
            
        except Exception as e:
            print(f"❌ Neo4j update failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _transform_for_neo4j(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform JSON data for Neo4j ingestion with sender/receiver extraction"""
        transformed = []
        sender_receiver_count = 0
        
        for i, record in enumerate(data):
            if i % 1000 == 0 and i > 0:
                print(f"      Processed {i}/{len(data)} records...")
            
            # Extract basic fields
            transformed_record = {
                "id": record.get("id", f"record_{i}"),
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "description": record.get("description", ""),
            }
            
            # Extract sender/receiver (use existing data structure or extract from name)
            sender = record.get("sender")
            receiver = record.get("receiver")
            
            # If sender/receiver are objects with 'name', use them
            if isinstance(sender, dict) and sender.get("name"):
                transformed_record["sender"] = {"name": sender["name"]}
                sender_receiver_count += 1
            elif isinstance(sender, str) and sender:
                transformed_record["sender"] = {"name": sender}
                sender_receiver_count += 1
            else:
                # Try to extract from name
                sender_from_name, _ = self._extract_sender_receiver_from_name(record.get("name", ""))
                if sender_from_name:
                    transformed_record["sender"] = {"name": sender_from_name}
                    sender_receiver_count += 1
            
            if isinstance(receiver, dict) and receiver.get("name"):
                transformed_record["receiver"] = {"name": receiver["name"]}
                sender_receiver_count += 1
            elif isinstance(receiver, str) and receiver:
                transformed_record["receiver"] = {"name": receiver}
                sender_receiver_count += 1
            else:
                # Try to extract from name
                _, receiver_from_name = self._extract_sender_receiver_from_name(record.get("name", ""))
                if receiver_from_name:
                    transformed_record["receiver"] = {"name": receiver_from_name}
                    sender_receiver_count += 1
            
            # Add metadata, properties, tags if present
            if record.get("metadata"):
                transformed_record["metadata"] = record["metadata"]
            if record.get("properties"):
                transformed_record["properties"] = record["properties"]
            if record.get("tags"):
                transformed_record["tags"] = record["tags"]
            
            transformed.append(transformed_record)
        
        print(f"      Transformed {len(transformed)} records")
        print(f"      Found sender/receiver in {sender_receiver_count} instances")
        return transformed
    
    def _extract_sender_receiver_from_name(self, name: str) -> tuple[Optional[str], Optional[str]]:
        """Extract sender and receiver from interface name"""
        sender = None
        receiver = None
        
        patterns = [
            r'from\s+([A-Za-z0-9\s]+?)\s+to\s+([A-Za-z0-9\s]+?)(?:\s|$)',
            r'([A-Za-z0-9\s]+?)\s+to\s+([A-Za-z0-9\s]+?)(?:\s|$)',
            r'([A-Za-z0-9\s]+?)\s*\|\s*([A-Za-z0-9\s]+?)(?:\s|$)',
            r'([A-Za-z0-9\s]+?)\s*->\s*([A-Za-z0-9\s]+?)(?:\s|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                sender = match.group(1).strip()
                receiver = match.group(2).strip()
                break
        
        # Clean up common words
        if sender:
            sender = re.sub(r'\b(interface|api|service|system)\b', '', sender, flags=re.IGNORECASE).strip()
        if receiver:
            receiver = re.sub(r'\b(interface|api|service|system)\b', '', receiver, flags=re.IGNORECASE).strip()
        
        return sender, receiver
    
    def sync_all(self, output_json: Optional[str] = None, update_duckdb: bool = True, 
                 update_neo4j: bool = True, max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Complete sync: Fetch live data and update all storage systems
        
        Args:
            output_json: Custom JSON filename (default: auto-generated)
            update_duckdb: Whether to update DuckDB
            update_neo4j: Whether to update Neo4j
            max_records: Maximum records to fetch (None = all)
        
        Returns:
            Dict with sync results
        """
        print("\n" + "=" * 70)
        print("🔄 LIVE DATA SYNC - FULL SYNCHRONIZATION")
        print("=" * 70)
        
        start_time = time.time()
        results = {
            "start_time": datetime.now().isoformat(),
            "success": True,
            "steps": {}
        }
        
        try:
            # Step 1: Fetch live data
            print("\n📥 STEP 1: FETCH LIVE DATA")
            print("-" * 70)
            data = self.fetch_live_data(max_records=max_records)
            results["steps"]["fetch"] = {
                "success": True,
                "record_count": len(data)
            }
            
            if not data:
                print("⚠️  No data fetched. Aborting sync.")
                results["success"] = False
                return results
            
            # Step 2: Save to JSON
            print("\n💾 STEP 2: SAVE TO JSON")
            print("-" * 70)
            json_file = self.save_to_json(data, output_json)
            results["steps"]["json"] = {
                "success": True,
                "filename": json_file
            }
            
            # Step 3: Update DuckDB
            if update_duckdb:
                print("\n🦆 STEP 3: UPDATE DUCKDB")
                print("-" * 70)
                duckdb_success = self.update_duckdb(json_file)
                results["steps"]["duckdb"] = {
                    "success": duckdb_success
                }
            
            # Step 4: Update Neo4j
            if update_neo4j:
                print("\n🕸️  STEP 4: UPDATE NEO4J")
                print("-" * 70)
                neo4j_success = self.update_neo4j(json_file)
                results["steps"]["neo4j"] = {
                    "success": neo4j_success
                }
            
            # Summary
            elapsed = time.time() - start_time
            results["end_time"] = datetime.now().isoformat()
            results["elapsed_seconds"] = elapsed
            
            print("\n" + "=" * 70)
            print("✅ SYNC COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print(f"⏱️  Total time: {elapsed:.2f} seconds")
            print(f"📊 Records processed: {len(data)}")
            print(f"📄 JSON file: {json_file}")
            print(f"🦆 DuckDB: {'✅ Updated' if results['steps'].get('duckdb', {}).get('success') else '⏭️  Skipped'}")
            print(f"🕸️  Neo4j: {'✅ Updated' if results['steps'].get('neo4j', {}).get('success') else '⏭️  Skipped'}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ SYNC FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            results["success"] = False
            results["error"] = str(e)
            return results


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Live Data Sync - Fetch API data and update all storage systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full sync (fetch + update all)
  python live_data_sync.py --full
  
  # Fetch only (save to JSON)
  python live_data_sync.py --fetch-only --output my_data.json
  
  # Update DuckDB and Neo4j from existing JSON
  python live_data_sync.py --update-from api_data_28-10-2025_143020.json
  
  # Fetch limited records for testing
  python live_data_sync.py --full --max-records 1000
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--full', action='store_true', 
                           help='Full sync: fetch + update all systems')
    mode_group.add_argument('--fetch-only', action='store_true',
                           help='Only fetch and save to JSON')
    mode_group.add_argument('--update-from', type=str, metavar='FILE',
                           help='Update DuckDB and Neo4j from existing JSON file')
    
    # Options
    parser.add_argument('--output', '-o', type=str,
                       help='Output JSON filename')
    parser.add_argument('--max-records', type=int,
                       help='Maximum records to fetch (for testing)')
    parser.add_argument('--skip-duckdb', action='store_true',
                       help='Skip DuckDB update')
    parser.add_argument('--skip-neo4j', action='store_true',
                       help='Skip Neo4j update')
    parser.add_argument('--duckdb-path', type=str, default='duckdb_engine/wic.duckdb',
                       help='Path to DuckDB database')
    
    args = parser.parse_args()
    
    # Default to full sync if no mode specified
    if not any([args.full, args.fetch_only, args.update_from]):
        args.full = True
    
    try:
        syncer = LiveDataSync()
        
        if args.update_from:
            # Update from existing JSON
            print(f"\n📂 Updating storage systems from: {args.update_from}")
            
            if not Path(args.update_from).exists():
                print(f"❌ Error: File not found: {args.update_from}")
                sys.exit(1)
            
            if not args.skip_duckdb:
                syncer.update_duckdb(args.update_from, args.duckdb_path)
            
            if not args.skip_neo4j:
                syncer.update_neo4j(args.update_from)
        
        elif args.fetch_only:
            # Fetch only
            print("\n📥 Fetching live data...")
            data = syncer.fetch_live_data(max_records=args.max_records)
            
            if data:
                syncer.save_to_json(data, args.output)
            else:
                print("⚠️  No data fetched")
                sys.exit(1)
        
        else:  # Full sync
            results = syncer.sync_all(
                output_json=args.output,
                update_duckdb=not args.skip_duckdb,
                update_neo4j=not args.skip_neo4j,
                max_records=args.max_records
            )
            
            if not results["success"]:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

