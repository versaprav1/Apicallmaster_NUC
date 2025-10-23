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
    
    # Add common system names (case-insensitive) - prioritize these
    common_systems = [
        'salesforce', 'sap', 'azure', 'aws', 'mulesoft', 'servicenow', 
        'oracle', 'microsoft', 'google', 'amazon', 'ibm', 'workday',
        'snowflake', 'databricks', 'tableau', 'powerbi', 'qlik', 'ls',
        'oanda', 'bitcoin', 'ecb', 'eam', 'planned'
    ]
    
    q_lower = q.lower()
    for system in common_systems:
        if system in q_lower:
            seeds.append(system.title())  # Capitalize first letter
    
    # Add single TitleCase words that might be system names (but exclude common words)
    common_words = {'show', 'all', 'systems', 'connected', 'to', 'from', 'find', 'what', 'which', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'with', 'without', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'path', 'paths', 'interface', 'interfaces', 'data', 'flow', 'flows'}
    
    for m in re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', q):
        if len(m) > 2 and m.lower() not in common_words:  # Avoid common words
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


def run(query: str, data: List[Dict[str, Any]] | None = None, max_hops: int = 2, path_limit: int = 5, llm_model: str = None, llm_manager = None, **kwargs):
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
            
            # Neighborhood around first seed (assume system name) - increased limit for comprehensive results
            neighborhood = store.k_hop_neighborhood(seed_names=seed_variations, max_hops=max_hops, limit=1000)
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

        neighborhood_lines = [label_and_name(r) for r in neighborhood]  # Show ALL results, no limit
        path_count = len(paths)
        summary_lines: List[str] = []
        
        # Create a user-friendly summary
        if neighborhood_lines:
            summary_lines.append(f"🔍 **Found {len(neighborhood)} systems and interfaces connected to '{seeds[0] if seeds else 'your query'}':**")
            summary_lines.append("")
            
            # Group by type for better readability
            interfaces = []
            systems = []
            
            for line in neighborhood_lines:
                if 'Interface' in line:
                    interfaces.append(line)
                elif 'System' in line:
                    systems.append(line)
                else:
                    interfaces.append(line)  # Default to interfaces
            
            if systems:
                summary_lines.append("**Connected Systems:**")
                for system in systems[:10]:
                    name = system.split(':')[-1] if ':' in system else system
                    summary_lines.append(f"  • {name}")
                summary_lines.append("")
            
            if interfaces:
                summary_lines.append("**Related Interfaces:**")
                for interface in interfaces[:10]:
                    name = interface.split(':')[-1] if ':' in interface else interface
                    # Truncate long names
                    if len(name) > 60:
                        name = name[:57] + "..."
                    summary_lines.append(f"  • {name}")
                summary_lines.append("")
                
        if path_count:
            summary_lines.append(f"🛤️ **Found {path_count} direct paths** between the specified systems.")
            summary_lines.append("")
        
        if not neighborhood_lines and path_count == 0:
            # Try a fallback search for interfaces by name
            debug_info.append(f"  • No relationships found, trying fallback search...")
            fallback_results = []
            try:
                # Filter seeds to remove query words and keep actual system/interface names
                # Common query words that aren't system names
                query_words = {'find', 'show', 'get', 'all', 'list', 'the', 'and', 'what', 'which', 
                              'how', 'from', 'to', 'between', 'connected', 'connection', 'interface',
                              'interfaces', 'system', 'systems', 'path', 'paths', 'data', 'flow'}
                
                # Filter seeds: remove short seeds and query words, prioritize longer specific terms
                filtered_seeds = []
                for seed in seeds:
                    # Split multi-word seeds and check each word
                    words = seed.split()
                    if len(words) > 1:
                        # Keep only non-query words from multi-word seeds
                        meaningful_words = [w for w in words if w.lower() not in query_words and len(w) > 2]
                        filtered_seeds.extend(meaningful_words)
                    elif len(seed) > 2 and seed.lower() not in query_words:
                        # Keep single meaningful words
                        filtered_seeds.append(seed)
                
                # Remove duplicates while preserving order
                seen = set()
                unique_seeds = []
                for s in filtered_seeds:
                    if s.lower() not in seen:
                        seen.add(s.lower())
                        unique_seeds.append(s)
                
                seeds_to_search = unique_seeds if unique_seeds else seeds
                debug_info.append(f"  • Filtered seeds for search: {seeds_to_search}")
                
                # Search for each seed with OR logic (any match is good)
                # Prioritize longer, more specific seeds
                seeds_by_length = sorted(seeds_to_search, key=len, reverse=True)
                
                for seed in seeds_by_length:
                    # Skip very short seeds
                    if len(seed) <= 2:
                        continue
                        
                    # Use toString() to safely handle non-string type values
                    cypher = """
                    MATCH (i:Interface) 
                    WHERE toLower(i.name) CONTAINS toLower($seed) 
                       OR (i.type IS NOT NULL AND toLower(toString(i.type)) CONTAINS toLower($seed))
                    RETURN DISTINCT i.name as name, i.type as type, labels(i) as labels
                    LIMIT 30
                    """
                    results = store.run_tx(cypher, seed=seed)
                    fallback_results.extend(results)
                    debug_info.append(f"  • Seed '{seed}' found {len(results)} interfaces")
                
                # Remove duplicates while preserving order
                seen_names = set()
                unique_results = []
                for result in fallback_results:
                    name = result.get('name', '')
                    if name and name not in seen_names:
                        seen_names.add(name)
                        unique_results.append(result)
                
                debug_info.append(f"  • Fallback search found {len(unique_results)} unique interfaces")
                
                if unique_results:
                    summary_lines.append(f"🔍 **Found {len(unique_results)} related interfaces (by name):**")
                    summary_lines.append("")
                    # Show up to 20 results instead of just 10
                    for result in unique_results[:20]:
                        name = result.get('name', 'Unknown')
                        interface_type = result.get('type', 'Unknown')
                        summary_lines.append(f"  • {name} ({interface_type})")
                else:
                    summary_lines.append("⚠️ **No results found.** Possible reasons:")
                    summary_lines.append("  • No data in Neo4j database")
                    summary_lines.append("  • Seeds not found in the data")
                    summary_lines.append("  • No relationships between the systems")
                    summary_lines.append(f"  • Search terms used: {', '.join(seeds)}")
                    
            except Exception as e:
                debug_info.append(f"  • Fallback search failed: {str(e)}")
                summary_lines.append("- ⚠️ No results found. Possible reasons:")
                summary_lines.append("  • No data in Neo4j database")
                summary_lines.append("  • Seeds not found in the data")
                summary_lines.append("  • No relationships between the systems")
                summary_lines.append("  • Neo4j connection issues")

        # Always show raw Neo4j results first
        raw_results = "\n".join(summary_lines)
        
        # If LLM model and manager are provided, add LLM synthesis
        if llm_model and llm_manager:
            try:
                # Collect all found results (from neighborhood OR fallback search)
                all_found_interfaces = []
                total_count = 0
                
                if neighborhood_lines:
                    # Use neighborhood results if available
                    all_found_interfaces = neighborhood_lines
                    total_count = len(neighborhood)
                elif 'unique_results' in locals() and unique_results:
                    # Use fallback search results
                    all_found_interfaces = [f"{r.get('name', 'Unknown')} (type: {r.get('type', 'Unknown')})" for r in unique_results]
                    total_count = len(unique_results)
                
                # Create a synthesis prompt with ALL available data (not limited)
                synthesis_prompt = f"""Based on the complete graph analysis results, provide a comprehensive and natural answer to the user's question.

User Question: {query}

Complete Graph Analysis Results:
- Search method: {"Relationship-based (k-hop neighborhood)" if neighborhood_lines else "Name-based search (fallback)"}
- Found {total_count} related interfaces
- Seeds identified: {', '.join(seeds)}
- All found interfaces: {', '.join(all_found_interfaces[:50])}  # Limit to first 50 for context

Please provide a clear, well-structured answer that:
1. Confirms the interfaces were found
2. Summarizes the main types or categories
3. Highlights any notable patterns
4. Answers the user's specific question"""

                # Use the selected LLM model to generate response
                llm_response = llm_manager.generate_response(
                    model_name=llm_model,
                    system_prompt="You are an expert in system integration and API analysis. Provide clear, helpful answers based on graph analysis results.",
                    user_prompt=synthesis_prompt
                )
                
                # Combine raw results and LLM response with clear headings
                combined_response = f"""## 🔍 Neo4j Query Results

{raw_results}

---

## 🤖 {llm_model} Response

{llm_response}"""
                
                # Update metadata to include LLM usage
                meta: Dict[str, Any] = {
                    "method": "graph_rag",
                    "backend": backend,
                    "seeds": seeds,
                    "neighborhood_count": len(neighborhood),
                    "paths_count": path_count,
                    "debug_info": debug_info,
                    "llm_model_used": llm_model,
                    "llm_synthesis": True,
                    "raw_results_count": len(neighborhood_lines),
                    "all_results_shown": True
                }
                
                return combined_response, meta
                
            except Exception as e:
                # If LLM synthesis fails, show raw results with error message
                debug_info.append(f"  • LLM synthesis failed: {str(e)}")
                error_response = f"""## 🔍 Neo4j Query Results

{raw_results}

---

## ⚠️ LLM Synthesis Failed

LLM synthesis failed with error: {str(e)}
Showing raw Neo4j results above."""
                
                meta: Dict[str, Any] = {
                    "method": "graph_rag",
                    "backend": backend,
                    "seeds": seeds,
                    "neighborhood_count": len(neighborhood),
                    "paths_count": path_count,
                    "debug_info": debug_info,
                    "llm_model_used": llm_model,
                    "llm_synthesis": False,
                    "llm_error": str(e),
                    "raw_results_count": len(neighborhood_lines),
                    "all_results_shown": True
                }
                
                return error_response, meta

        # If no LLM provided, just show raw results
        meta: Dict[str, Any] = {
            "method": "graph_rag",
            "backend": backend,
            "seeds": seeds,
            "neighborhood_count": len(neighborhood),
            "paths_count": path_count,
            "debug_info": debug_info,
            "raw_results_count": len(neighborhood_lines),
            "all_results_shown": True
        }
        return raw_results, meta
    finally:
        store.close()