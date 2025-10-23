"""
Quick diagnostic script to check Neo4j database and Ollama models.
Run this to diagnose issues with Graph RAG.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🔍 DIAGNOSTIC: Neo4j & Ollama Check")
print("=" * 70)

# ============================================================================
# 1. CHECK NEO4J CONNECTION AND DATA
# ============================================================================
print("\n1️⃣ Checking Neo4j Connection...")
print("-" * 70)

try:
    from src.neo4j_wrapper import test_connection, NEO4J_AVAILABLE
    
    if not NEO4J_AVAILABLE:
        print("❌ Neo4j driver not installed!")
        print("   Install with: pip install neo4j")
    else:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'pass')
        
        print(f"   URI: {uri}")
        print(f"   User: {user}")
        print(f"   Password: {'*' * len(password)}")
        
        success, message = test_connection(uri, (user, password))
        
        if success:
            print(f"✅ {message}")
            
            # Now check if there's data
            print("\n2️⃣ Checking Neo4j Data...")
            print("-" * 70)
            
            from src.graph_store_neo4j import Neo4jGraphStore
            store = Neo4jGraphStore(uri, user, password)
            
            try:
                # Count nodes
                result = store.run_tx("MATCH (n) RETURN count(n) as total")
                total_nodes = result[0]['total'] if result else 0
                print(f"   Total nodes: {total_nodes}")
                
                # Count by label
                result = store.run_tx("""
                    MATCH (n) 
                    RETURN labels(n)[0] as label, count(n) as count 
                    ORDER BY count DESC
                """)
                print("\n   Nodes by type:")
                for row in result[:10]:
                    label = row.get('label', 'Unknown')
                    count = row.get('count', 0)
                    print(f"     • {label}: {count}")
                
                # Sample interface names
                result = store.run_tx("""
                    MATCH (i:Interface) 
                    RETURN i.name as name, i.type as type 
                    LIMIT 10
                """)
                
                if result:
                    print("\n   Sample interfaces:")
                    for row in result:
                        name = row.get('name', 'Unknown')
                        itype = row.get('type', 'Unknown')
                        print(f"     • {name[:80]} (type: {itype})")
                else:
                    print("\n   ⚠️ No interfaces found!")
                
                # Check for APIM interfaces
                result = store.run_tx("""
                    MATCH (i:Interface) 
                    WHERE toLower(i.name) CONTAINS 'apim' 
                       OR toLower(i.type) CONTAINS 'apim'
                    RETURN count(i) as count
                """)
                apim_count = result[0]['count'] if result else 0
                print(f"\n   Interfaces with 'APIM': {apim_count}")
                
                # Check for IDOC interfaces
                result = store.run_tx("""
                    MATCH (i:Interface) 
                    WHERE toLower(i.name) CONTAINS 'idoc' 
                       OR toLower(i.type) CONTAINS 'idoc'
                    RETURN count(i) as count
                """)
                idoc_count = result[0]['count'] if result else 0
                print(f"   Interfaces with 'IDOC': {idoc_count}")
                
                if total_nodes == 0:
                    print("\n❌ Neo4j database is EMPTY!")
                    print("   You need to load data first. Check these scripts:")
                    print("     • ingest_to_neo4j_cloud.py")
                    print("     • final_ingest_to_neo4j.py")
                    print("     • smart_ingest_to_neo4j.py")
                else:
                    print(f"\n✅ Neo4j has {total_nodes} nodes")
                
                store.close()
                
            except Exception as e:
                print(f"❌ Error querying Neo4j: {e}")
                
        else:
            print(f"❌ {message}")
            print("\n   Common fixes:")
            print("     • Make sure Neo4j is running (check Neo4j Desktop or service)")
            print("     • Verify credentials in .env file")
            print("     • Check firewall/port 7687")
            
except Exception as e:
    print(f"❌ Error checking Neo4j: {e}")

# ============================================================================
# 2. CHECK OLLAMA
# ============================================================================
print("\n\n3️⃣ Checking Ollama...")
print("-" * 70)

try:
    import requests
    
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    
    if response.status_code == 200:
        print("✅ Ollama is running")
        
        data = response.json()
        models = data.get('models', [])
        
        print(f"\n   Available models: {len(models)}")
        print()
        
        deepseek_found = False
        for model in models:
            name = model.get('name', 'unknown')
            size = model.get('size', 0) / (1024**3)  # Convert to GB
            print(f"     • {name} ({size:.1f} GB)")
            
            if 'deepseek' in name.lower():
                deepseek_found = True
        
        print()
        if deepseek_found:
            print("✅ DeepSeek model found")
        else:
            print("❌ DeepSeek model NOT found!")
            print("   Install with: ollama pull deepseek-r1:14b")
        
        # Check specific model
        print("\n   Testing deepseek-r1:14b...")
        test_payload = {
            "model": "deepseek-r1:14b",
            "prompt": "Hello",
            "stream": False
        }
        
        try:
            test_response = requests.post(
                "http://localhost:11434/api/generate",
                json=test_payload,
                timeout=10
            )
            
            if test_response.status_code == 200:
                print("   ✅ deepseek-r1:14b is working!")
            else:
                print(f"   ❌ Error: {test_response.status_code}")
                print(f"   Response: {test_response.text}")
                
        except Exception as e:
            print(f"   ❌ Error testing model: {e}")
            
    else:
        print(f"❌ Ollama returned status {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to Ollama at localhost:11434")
    print("   Make sure Ollama is running:")
    print("     • Windows: Check if Ollama service is running")
    print("     • Start with: ollama serve")
    
except Exception as e:
    print(f"❌ Error checking Ollama: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("📋 SUMMARY")
print("=" * 70)
print("\nIf you see errors above, fix them in this order:")
print("  1. Make sure Neo4j is running and has data")
print("  2. Make sure Ollama is running")
print("  3. Make sure required models are installed")
print("\nThen restart your Streamlit app.")
print("=" * 70)


