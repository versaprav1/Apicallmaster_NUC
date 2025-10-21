"""
Graph RAG (knowledge graph retrieval) method backed by Neo4j (configurable).

Environment:
  - GRAPH_BACKEND=neo4j (default) | networkx (future)
  - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

This implementation focuses on system/interface relationships:
  - k-hop neighborhood around mentioned systems
  - shortest paths between sender and receiver if both are present
"""

from typing import Any, Dict, List, Tuple
import os

def _extract_names_from_query(q: str) -> List[str]:
    # Enhanced heuristic: extract system names from queries
    import re
    seeds: List[str] = []
    
    # Extract quoted terms
    seeds.extend(re.findall(r'"([^"]+)"', q))
    seeds.extend(re.findall(r"'([^']+)'", q))
    
    # Add TitleCase multi-words (e.g., "System A", "Azure Data Factory")
    for m in re.findall(r'(?:[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)+)', q):
        seeds.append(m.strip())
    
    # Add common system names (case-insensitive)
    common_systems = [
        'salesforce', 'sap', 'azure', 'aws', 'mulesoft', 'servicenow', 
        'oracle', 'microsoft', 'google', 'amazon', 'ibm', 'workday',
        'snowflake', 'databricks', 'tableau', 'powerbi', 'qlik'
    ]
    
    q_lower = q.lower()
    for system in common_systems:
        if system in q_lower:
            seeds.append(system.title())  # Capitalize first letter
    
    # Add single TitleCase words that might be system names
    for m in re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', q):
        if len(m) > 2:  # Avoid short words like "The", "To", etc.
            seeds.append(m)
    
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for s in seeds:
        s_clean = s.strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            out.append(s_clean)
    
    return out


def run(query: str, data: List[Dict[str, Any]] | None = None, max_hops: int = 2, path_limit: int = 5, **kwargs):
    """
    Graph RAG: Query Neo4j graph database for relationship analysis
    
    This method ONLY works with Neo4j graph database.
    It does NOT ingest data - data must be pre-loaded into Neo4j.
    
    For data ingestion, use separate ingestion scripts or tools.
    
    Args:
        query: User query to analyze
        data: DEPRECATED - No longer used. Data must be pre-loaded in Neo4j
        max_hops: Maximum hops for neighborhood search
        path_limit: Maximum number of paths to return
        **kwargs: Additional parameters
    
    Returns:
        Tuple of (summary: str, metadata: dict)
    """
    backend = os.getenv("GRAPH_BACKEND", "neo4j").lower()
    if backend != "neo4j":
        raise NotImplementedError("Only Neo4j backend is implemented currently. Set GRAPH_BACKEND=neo4j.")

    # Lazy import to avoid hard dependency when unused
    from src.graph_store_neo4j import Neo4jGraphStore

    # Debug information
    debug_info = []
    debug_info.append(f"🔍 Graph RAG - Neo4j Query Mode:")
    debug_info.append(f"  • Query: '{query}'")
    debug_info.append(f"  • Backend: {backend}")
    debug_info.append(f"  • Max hops: {max_hops}")
    debug_info.append(f"  • Path limit: {path_limit}")
    debug_info.append(f"  • Mode: Query existing Neo4j data (no ingestion)")

    # Warn if data was provided (it's deprecated)
    if data:
        debug_info.append(f"  • ⚠️ WARNING: 'data' parameter is deprecated and will be ignored")
        debug_info.append(f"  • ⚠️ Graph RAG only queries existing Neo4j data")
        debug_info.append(f"  • ⚠️ For data ingestion, use separate ingestion scripts")

    store = Neo4jGraphStore()
    try:

        # Extract seeds from query
        seeds = _extract_names_from_query(query)
        debug_info.append(f"  • Extracted seeds: {seeds}")

        neighborhood: List[Dict[str, Any]] = []
        paths: List[Dict[str, Any]] = []

        if seeds:
            debug_info.append(f"  • Searching neighborhood around seed: '{seeds[0]}'")
            # Try different variations of the seed name
            seed_variations = [seeds[0], seeds[0].lower(), seeds[0].upper(), seeds[0].title()]
            debug_info.append(f"  • Seed variations: {seed_variations}")
            
            # Neighborhood around first seed (assume system name)
            neighborhood = store.k_hop_neighborhood(seed_names=seed_variations, max_hops=max_hops, limit=200)
            debug_info.append(f"  • Found {len(neighborhood)} neighborhood nodes")

        # If the query appears to mention a sender and a receiver (two seeds), try shortest path
        if len(seeds) >= 2:
            debug_info.append(f"  • Searching shortest path from '{seeds[0]}' to '{seeds[1]}'")
            paths = store.shortest_paths(seeds[0], seeds[1], limit=path_limit)
            debug_info.append(f"  • Found {len(paths)} shortest paths")

        # Check if we have any data in Neo4j at all
        try:
            total_nodes = store.run_tx("MATCH (n) RETURN count(n) as total")
            if total_nodes and len(total_nodes) > 0:
                total_count = total_nodes[0].get('total', 0)
                debug_info.append(f"  • Total nodes in Neo4j: {total_count}")
                
                if total_count == 0:
                    debug_info.append(f"  • ⚠️ No data in Neo4j database!")
            else:
                debug_info.append(f"  • ⚠️ Could not check Neo4j node count")
        except Exception as e:
            debug_info.append(f"  • ⚠️ Error checking Neo4j: {str(e)}")

        # Format summary
        def label_and_name(node_record: Dict[str, Any]) -> str:
            labels = node_record.get('labels', [])
            node = node_record.get('node', {})
            name = node.get('name') if isinstance(node, dict) else None
            return f"{labels}:{name}" if name else f"{labels}"

        neighborhood_lines = [label_and_name(r) for r in neighborhood][:20]
        path_count = len(paths)
        summary_lines: List[str] = []
        summary_lines.append(f"Graph RAG (Neo4j) results for query '{query}':")
        
        # Add debug info to summary
        summary_lines.extend(debug_info)
        
        if neighborhood_lines:
            summary_lines.append("- Neighborhood (sample):")
            summary_lines.extend([f"  • {line}" for line in neighborhood_lines])
        if path_count:
            summary_lines.append(f"- Shortest paths found: {path_count} (showing up to {path_limit})")
        
        if not neighborhood_lines and path_count == 0:
            # Try a fallback search for interfaces by name
            debug_info.append(f"  • No relationships found, trying fallback search...")
            fallback_results = []
            try:
                for seed in seeds:
                    # Search for interfaces that contain the seed name
                    cypher = """
                    MATCH (i:Interface) 
                    WHERE toLower(i.name) CONTAINS toLower($seed)
                    RETURN i.name as name, i.type as type, labels(i) as labels
                    LIMIT 10
                    """
                    results = store.run_tx(cypher, seed=seed)
                    fallback_results.extend(results)
                
                debug_info.append(f"  • Fallback search found {len(fallback_results)} interfaces")
                
                if fallback_results:
                    summary_lines.append("- 🔍 Found related interfaces (by name):")
                    for result in fallback_results[:10]:
                        name = result.get('name', 'Unknown')
                        interface_type = result.get('type', 'Unknown')
                        summary_lines.append(f"  • {name} ({interface_type})")
                else:
                    summary_lines.append("- ⚠️ No results found. Possible reasons:")
                    summary_lines.append("  • No data in Neo4j database")
                    summary_lines.append("  • Seeds not found in the data")
                    summary_lines.append("  • No relationships between the systems")
                    summary_lines.append("  • Neo4j connection issues")
                    
            except Exception as e:
                debug_info.append(f"  • Fallback search failed: {str(e)}")
                summary_lines.append("- ⚠️ No results found. Possible reasons:")
                summary_lines.append("  • No data in Neo4j database")
                summary_lines.append("  • Seeds not found in the data")
                summary_lines.append("  • No relationships between the systems")
                summary_lines.append("  • Neo4j connection issues")

        meta: Dict[str, Any] = {
            "method": "graph_rag",
            "backend": backend,
            "seeds": seeds,
            "neighborhood_count": len(neighborhood),
            "paths_count": path_count,
            "debug_info": debug_info
        }
        return "\n".join(summary_lines), meta
    finally:
        store.close()