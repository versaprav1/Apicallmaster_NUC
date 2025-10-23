"""
Test Neo4j Cloud (AuraDB) connection and check for data.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("☁️  NEO4J CLOUD (AURADB) DIAGNOSTIC")
print("=" * 70)

# Get credentials from environment or use the ones from your UI
uri = os.getenv('NEO4J_URI', 'neo4j+s://3ec8636d.databases.neo4j.io')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '')

print(f"\n📍 Connection Details:")
print(f"  URI: {uri}")
print(f"  User: {user}")
print(f"  Password: {'*' * len(password) if password else '[NOT SET]'}")
print(f"  Protocol: {'AuraDB (TLS)' if 'neo4j+s://' in uri else 'Local'}")

# ============================================================================
# TEST CONNECTION
# ============================================================================
print(f"\n1️⃣ Testing connection to Neo4j Cloud...")
print("-" * 70)

try:
    from src.graph_store_neo4j import Neo4jGraphStore
    import time
    
    start = time.time()
    store = Neo4jGraphStore(uri, user, password)
    connect_time = time.time() - start
    
    print(f"✅ Connected in {connect_time:.2f}s")
    
    # ========================================================================
    # CHECK DATABASE CONTENT
    # ========================================================================
    print(f"\n2️⃣ Checking database content...")
    print("-" * 70)
    
    # Count all nodes
    start = time.time()
    result = store.run_tx("MATCH (n) RETURN count(n) as total")
    query_time = time.time() - start
    
    total_nodes = result[0]['total'] if result else 0
    print(f"  Total nodes: {total_nodes} (query took {query_time:.2f}s)")
    
    if total_nodes == 0:
        print(f"\n❌ DATABASE IS EMPTY!")
        print(f"\n  Your Neo4j Cloud database has no data.")
        print(f"  You need to run an ingestion script to load data:")
        print(f"    • Update .env with NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        print(f"    • Run: python ingest_to_neo4j_cloud.py")
        print(f"    • Or: python smart_ingest_to_neo4j.py")
    else:
        # Count by label
        result = store.run_tx("""
            MATCH (n) 
            RETURN labels(n)[0] as label, count(n) as count 
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print(f"\n  Node distribution:")
        for row in result:
            label = row.get('label', 'Unknown')
            count = row.get('count', 0)
            print(f"    • {label}: {count:,}")
        
        # ====================================================================
        # CHECK FOR AZURE INTERFACES
        # ====================================================================
        print(f"\n3️⃣ Checking for Azure interfaces...")
        print("-" * 70)
        
        start = time.time()
        result = store.run_tx("""
            MATCH (i:Interface) 
            WHERE toLower(i.name) CONTAINS 'azure' 
               OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS 'azure')
            RETURN count(i) as count
        """)
        query_time = time.time() - start
        
        azure_count = result[0]['count'] if result else 0
        print(f"  Azure interfaces: {azure_count} (query took {query_time:.2f}s)")
        
        if azure_count > 0:
            # Show samples
            result = store.run_tx("""
                MATCH (i:Interface) 
                WHERE toLower(i.name) CONTAINS 'azure' 
                   OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS 'azure')
                RETURN i.name as name, i.type as type
                LIMIT 10
            """)
            
            print(f"\n  Sample Azure interfaces:")
            for row in result:
                name = row.get('name', 'Unknown')
                itype = row.get('type', 'Unknown')
                print(f"    • {name[:70]} (type: {itype})")
        else:
            print(f"\n  ⚠️  No Azure interfaces found in database")
            print(f"  The database has data but no Azure-related interfaces")
        
        # ====================================================================
        # PERFORMANCE TEST
        # ====================================================================
        print(f"\n4️⃣ Network latency test...")
        print("-" * 70)
        
        # Run 5 simple queries to measure average latency
        latencies = []
        for i in range(5):
            start = time.time()
            store.run_tx("RETURN 1")
            latencies.append(time.time() - start)
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"  Average query latency: {avg_latency*1000:.0f}ms")
        print(f"  Range: {min(latencies)*1000:.0f}ms - {max(latencies)*1000:.0f}ms")
        
        if avg_latency > 1.0:
            print(f"\n  ⚠️  High latency detected!")
            print(f"     Cloud databases have higher latency than local")
            print(f"     This is normal for AuraDB free tier")
        else:
            print(f"\n  ✅ Good latency for cloud database")
    
    store.close()
    
except ImportError as e:
    print(f"❌ Neo4j driver not available: {e}")
    print(f"   Install with: pip install neo4j")
    
except Exception as e:
    error_msg = str(e)
    print(f"❌ Connection failed: {error_msg}")
    
    if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
        print(f"\n  💡 Authentication failed - check your credentials:")
        print(f"     1. Verify password in Neo4j Aura console")
        print(f"     2. Update .env file with correct password")
        print(f"     3. Restart your app")
    elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
        print(f"\n  💡 Connection failed - check your database:")
        print(f"     1. Verify database is running in Neo4j Aura")
        print(f"     2. Check URI is correct: {uri}")
        print(f"     3. Verify firewall allows connection")
    else:
        print(f"\n  💡 Unexpected error - check:")
        print(f"     1. Neo4j driver is installed: pip install neo4j")
        print(f"     2. Credentials are correct")
        print(f"     3. Database is running")

# ============================================================================
# SUMMARY
# ============================================================================
print(f"\n" + "=" * 70)
print(f"📊 SUMMARY")
print(f"=" * 70)

if total_nodes == 0:
    print(f"""
❌ Your Neo4j Cloud database is EMPTY

Next steps:
1. Add your Neo4j Cloud credentials to .env:
   NEO4J_URI=neo4j+s://3ec8636d.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here

2. Run ingestion script:
   python ingest_to_neo4j_cloud.py
   
3. Verify data was loaded:
   python test_neo4j_cloud.py
""")
else:
    print(f"""
✅ Neo4j Cloud is working!

• Total nodes: {total_nodes:,}
• Azure interfaces: {azure_count if 'azure_count' in locals() else 'Error checking'}

Note: Cloud databases have higher latency than local Neo4j.
The 51-second execution time you saw is likely due to:
  1. Initial connection setup (~2-5s)
  2. Network latency per query (~500-1000ms)
  3. Multiple query attempts in Graph RAG
""")

print(f"=" * 70)

