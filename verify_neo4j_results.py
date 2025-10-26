"""
Verify if Neo4j Graph RAG results are correct for "List SAP interfaces"
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🔍 VERIFYING NEO4J RESULTS FOR 'List SAP interfaces'")
print("=" * 70)

# Connect to Neo4j
uri = os.getenv('NEO4J_URI', 'neo4j+s://3ec8636d.databases.neo4j.io')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '')

print(f"\n📍 Connecting to: {uri}")

try:
    from src.graph_store_neo4j import Neo4jGraphStore
    
    store = Neo4jGraphStore(uri, user, password)
    
    # ========================================================================
    # SIMULATE WHAT GRAPH RAG DOES
    # ========================================================================
    
    query = "List SAP interfaces"
    print(f"\n📝 Query: '{query}'")
    print("-" * 70)
    
    # Step 1: Extract seeds (simulating what graph_rag.py does)
    import re
    seeds = []
    
    # Extract quoted terms
    seeds.extend(re.findall(r'"([^"]+)"', query))
    seeds.extend(re.findall(r"'([^']+)'", query))
    
    # Add TitleCase multi-words
    for m in re.findall(r'(?:[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)+)', query):
        seeds.append(m.strip())
    
    # Add common systems
    common_systems = ['salesforce', 'sap', 'azure', 'aws', 'mulesoft']
    q_lower = query.lower()
    for system in common_systems:
        if system in q_lower:
            seeds.append(system.title())
    
    # Add single TitleCase words
    common_words = {'show', 'all', 'systems', 'connected', 'to', 'from', 'find', 
                   'what', 'which', 'the', 'list', 'interface', 'interfaces'}
    for m in re.findall(r'\b[A-Z][a-zA-Z]+\b', query):
        if len(m) > 2 and m.lower() not in common_words:
            seeds.append(m)
    
    # Deduplicate
    seen = set()
    unique_seeds = []
    for s in seeds:
        s_clean = s.strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            unique_seeds.append(s_clean)
    
    print(f"1️⃣ Seeds extracted: {unique_seeds}")
    
    # Step 2: Filter seeds (what my code does)
    query_words = {'find', 'show', 'get', 'all', 'list', 'the', 'and', 'what', 'which',
                  'how', 'from', 'to', 'between', 'connected', 'connection', 'interface',
                  'interfaces', 'system', 'systems', 'path', 'paths', 'data', 'flow'}
    
    filtered_seeds = []
    for seed in unique_seeds:
        words = seed.split()
        if len(words) > 1:
            meaningful_words = [w for w in words if w.lower() not in query_words and len(w) > 2]
            filtered_seeds.extend(meaningful_words)
        elif len(seed) > 2 and seed.lower() not in query_words:
            filtered_seeds.append(seed)
    
    # Remove duplicates
    seen = set()
    final_seeds = []
    for s in filtered_seeds:
        if s.lower() not in seen:
            seen.add(s.lower())
            final_seeds.append(s)
    
    print(f"2️⃣ Filtered seeds: {final_seeds}")
    
    # Step 3: Search for each seed
    print(f"\n3️⃣ Searching Neo4j...")
    print("-" * 70)
    
    all_results = []
    
    for seed in final_seeds:
        cypher = """
        MATCH (i:Interface) 
        WHERE toLower(i.name) CONTAINS toLower($seed) 
           OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS toLower($seed))
        RETURN DISTINCT i.name as name, i.type as type, labels(i) as labels
        LIMIT 30
        """
        
        results = store.run_tx(cypher, seed=seed)
        print(f"\n  Seed '{seed}': Found {len(results)} interfaces")
        
        all_results.extend(results)
    
    # Deduplicate
    seen_names = set()
    unique_results = []
    for result in all_results:
        name = result.get('name', '')
        if name and name not in seen_names:
            seen_names.add(name)
            unique_results.append(result)
    
    print(f"\n4️⃣ Total unique results: {len(unique_results)}")
    print("-" * 70)
    
    # Show first 30
    print(f"\n📊 First 30 results (what UI shows):")
    for i, result in enumerate(unique_results[:30], 1):
        name = result.get('name', 'Unknown')
        itype = result.get('type', 'Unknown')
        # Check if 'SAP' is in the name
        has_sap = 'sap' in name.lower()
        marker = "✅" if has_sap else "⚠️"
        print(f"  {marker} {i}. {name[:70]} (type: {itype})")
    
    # ========================================================================
    # VERIFICATION: Check if results are correct
    # ========================================================================
    
    print(f"\n" + "=" * 70)
    print("🧪 VERIFICATION")
    print("=" * 70)
    
    # Count how many actually contain 'SAP'
    sap_count = sum(1 for r in unique_results if 'sap' in r.get('name', '').lower())
    non_sap_count = len(unique_results) - sap_count
    
    print(f"\n✅ Interfaces with 'SAP' in name: {sap_count}/{len(unique_results)}")
    print(f"⚠️  Interfaces WITHOUT 'SAP' in name: {non_sap_count}/{len(unique_results)}")
    
    if non_sap_count > 0:
        print(f"\n⚠️  Non-SAP interfaces found:")
        for r in unique_results:
            name = r.get('name', '')
            if 'sap' not in name.lower():
                print(f"    • {name[:70]}")
    
    # Check: Are we missing SAP interfaces?
    print(f"\n5️⃣ Checking for missed SAP interfaces...")
    print("-" * 70)
    
    # Count total SAP interfaces in database
    total_sap = store.run_tx("""
        MATCH (i:Interface)
        WHERE toLower(i.name) CONTAINS 'sap'
           OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS 'sap')
        RETURN count(i) as count
    """)
    
    total_sap_count = total_sap[0]['count'] if total_sap else 0
    
    print(f"  Total SAP interfaces in database: {total_sap_count}")
    print(f"  Returned by Graph RAG: {len(unique_results)}")
    print(f"  Missing: {total_sap_count - len(unique_results)}")
    
    if total_sap_count > len(unique_results):
        print(f"\n  ⚠️  Some SAP interfaces were not returned!")
        print(f"  Reason: LIMIT 30 per seed restricts results")
        print(f"  FIX: Increase LIMIT or show all results")
    
    # Sample some interfaces we might be missing
    if total_sap_count > len(unique_results):
        print(f"\n  📋 Sample of interfaces NOT shown:")
        
        returned_names = [r.get('name') for r in unique_results]
        params = {'returned': returned_names}
        
        missing = store.run_tx("""
            MATCH (i:Interface)
            WHERE (toLower(i.name) CONTAINS 'sap' 
                OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS 'sap'))
              AND NOT i.name IN $returned
            RETURN i.name as name, i.type as type
            LIMIT 10
        """, returned=returned_names)
        
        for m in missing:
            print(f"    • {m.get('name', 'Unknown')} (type: {m.get('type', 'Unknown')})")
    
    # ========================================================================
    # FINAL VERDICT
    # ========================================================================
    
    print(f"\n" + "=" * 70)
    print("⚖️  VERDICT")
    print("=" * 70)
    
    if sap_count == len(unique_results):
        print(f"\n✅ RESULTS ARE CORRECT!")
        print(f"   All {len(unique_results)} results contain 'SAP'")
    else:
        print(f"\n⚠️  RESULTS HAVE ISSUES!")
        print(f"   {non_sap_count} results do NOT contain 'SAP'")
    
    if total_sap_count > len(unique_results):
        print(f"\n⚠️  INCOMPLETE RESULTS!")
        print(f"   Database has {total_sap_count} SAP interfaces")
        print(f"   Only showing {len(unique_results)} (due to LIMIT 30)")
        print(f"\n   RECOMMENDATION: Increase LIMIT from 30 to {min(total_sap_count, 100)}")
    else:
        print(f"\n✅ COMPLETE RESULTS!")
        print(f"   All {total_sap_count} SAP interfaces are shown")
    
    store.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)


