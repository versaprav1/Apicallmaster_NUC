"""
Vector RAG (semantic retrieval) method.
Retrieves top-k relevant chunks using vector similarity via ChromaDB.

This method uses the VectorKnowledgeStore (ChromaDB) to perform semantic search
and retrieve the most relevant interface data based on the user's query.
"""

import os
from typing import Dict, List, Any, Optional
from src.vector_knowledge_store import VectorKnowledgeStore
from sentence_transformers import SentenceTransformer


def _store_qa_pair(query: str, answer: str, data_source: str, intent: Optional[str], 
                   top_k: int, similarity_threshold: float, meta: Dict[str, Any]) -> None:
    """
    Helper function to store Q&A pairs in the vector knowledge store.
    
    Args:
        query: User's question
        answer: Generated answer
        data_source: Data source used
        intent: Intent dict or string
        top_k: Number of results retrieved
        similarity_threshold: Threshold used
        meta: Metadata from the search
    """
    try:
        vector_store = VectorKnowledgeStore()
        
        # Extract intent string if it's a dict
        intent_str = "vector_search"
        if isinstance(intent, dict):
            intent_str = intent.get('query_type', 'api')
        elif isinstance(intent, str):
            intent_str = intent
        
        # Store the Q&A pair with metadata
        vector_store.store_qa_pair(
            question=query,
            answer=answer if isinstance(answer, str) else str(answer),
            query={},  # Empty for vector searches (no API query)
            endpoint="local_json" if data_source == "local_json" else data_source,
            intent=intent_str,
            data_source=data_source,
            method="vector_rag",
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            extra_metadata={
                "strategy": meta.get("strategy", "unknown"),
                "retrieved": meta.get("retrieved", 0),
                "avg_similarity": meta.get("avg_similarity", 0),
                "llm_synthesis": meta.get("llm_synthesis", False),
                "llm_model_used": meta.get("llm_model_used", "none")
            }
        )
    except Exception as e:
        # Non-fatal: just log the error
        print(f"Warning: Could not store Q&A pair: {e}")


def run(query: str, data: Optional[List[Dict[str, Any]]] = None, top_k: int = 5, 
        data_source: str = "duckdb", intent: Optional[str] = None, 
        similarity_threshold: float = 0.3, llm_model: str = None, llm_manager = None, **kwargs) -> tuple[str, Dict[str, Any]]:
    """
    Vector RAG: retrieve top-k relevant chunks using semantic search.
    
    This method performs semantic search using ChromaDB to find the most relevant
    interface data based on the user's query. It can search through previously
    stored Q&A pairs or perform direct semantic matching on provided data.
    
    Args:
        query: The user query or prompt
        data: Optional list of data items to search (if not using stored Q&A pairs)
        top_k: Number of top relevant chunks to return (default: 5)
        data_source: Data source to search ("duckdb", "api", or "both")
        intent: Optional intent filter for more targeted search
        similarity_threshold: Minimum similarity score (0-1) for results
        **kwargs: Additional parameters
    
    Returns:
        summary: The retrieved relevant chunks formatted as a string
        meta: Metadata about the retrieval process
    """
    try:
        # Initialize vector store
        vector_store = VectorKnowledgeStore()
        
        # Extract intent string from intent dict if it's a dict
        intent_str = None
        if isinstance(intent, dict):
            intent_str = intent.get('query_type') or intent.get('intent')
        elif isinstance(intent, str):
            intent_str = intent
        
        # Strategy 1: Search stored Q&A pairs first
        similar_qa = vector_store.find_similar_qa(
            question=query,
            data_source=data_source,
            intent=intent_str,
            top_k=top_k
        )
        
        # Filter by similarity threshold
        relevant_qa = [
            qa for qa in similar_qa 
            if qa.get('similarity', 0) >= similarity_threshold
        ]
        
        if relevant_qa:
            # Found relevant Q&A pairs - use them
            summary_parts = [
                f"📚 Found {len(relevant_qa)} relevant Q&A pairs from knowledge base:\n"
            ]
            
            for i, qa in enumerate(relevant_qa, 1):
                similarity = qa.get('similarity', 0) * 100
                question = qa.get('question', 'N/A')
                answer = qa.get('answer', 'N/A')
                metadata = qa.get('metadata', {})
                
                summary_parts.append(
                    f"\n**Result {i}** (Similarity: {similarity:.1f}%)\n"
                    f"**Question:** {question}\n"
                    f"**Answer:** {answer[:300]}{'...' if len(answer) > 300 else ''}\n"
                    f"**Source:** {metadata.get('data_source', 'unknown')}\n"
                )
            
            raw_summary = "\n".join(summary_parts)
            
            meta = {
                "method": "vector_rag",
                "strategy": "qa_pairs",
                "top_k": top_k,
                "retrieved": len(relevant_qa),
                "similarity_threshold": similarity_threshold,
                "data_source": data_source,
                "intent": intent,
                "avg_similarity": sum(qa.get('similarity', 0) for qa in relevant_qa) / len(relevant_qa) if relevant_qa else 0
            }
            
            # Add LLM synthesis if model and manager are provided
            if llm_model and llm_manager:
                try:
                    # Create synthesis prompt with all retrieved data
                    synthesis_prompt = f"""Based on the vector search results, provide a comprehensive and natural answer to the user's question.

User Question: {query}

Vector Search Results:
- Found {len(relevant_qa)} relevant Q&A pairs
- Average similarity: {sum(qa.get('similarity', 0) for qa in relevant_qa) / len(relevant_qa):.3f}
- Data source: {data_source}

Retrieved Q&A Pairs:
{raw_summary}

Please provide a clear, well-structured answer that explains the relevant information found, focusing on the most important details for the user's question."""

                    # Use the selected LLM model to generate response
                    llm_response = llm_manager.generate_response(
                        model_name=llm_model,
                        system_prompt="You are an expert in data analysis and information retrieval. Provide clear, helpful answers based on vector search results.",
                        user_prompt=synthesis_prompt
                    )
                    
                    # Combine raw results and LLM response with clear headings
                    combined_response = f"""# 📚 Knowledge Base Search Report

## 🔍 Cached Q&A Results
**Found:** {len(relevant_qa)} similar questions  
**Data Source:** {data_source}  
**Average Similarity:** {sum(qa.get('similarity', 0) for qa in relevant_qa) / len(relevant_qa) * 100:.1f}%  

{raw_summary}

---

## 🤖 AI Synthesis by {llm_model}

{llm_response}

---

### 💡 Search Metadata
- **LLM Model:** {llm_model}
- **Strategy:** Q&A Pairs from Knowledge Base
- **Results Retrieved:** {len(relevant_qa)}"""
                    
                    # Update metadata to include LLM usage
                    meta.update({
                        "llm_model_used": llm_model,
                        "llm_synthesis": True,
                        "raw_results_count": len(relevant_qa),
                        "all_results_shown": True
                    })
                    
                    return combined_response, meta
                    
                except Exception as e:
                    # If LLM synthesis fails, show raw results with error message
                    error_response = f"""# 📚 Knowledge Base Search Report

## 🔍 Cached Q&A Results
**Found:** {len(relevant_qa)} similar questions  

{raw_summary}

---

## ⚠️ LLM Synthesis Failed

**Error:** {str(e)}

The raw Q&A results are shown above. LLM synthesis could not be completed."""
                    
                    meta.update({
                        "llm_model_used": llm_model,
                        "llm_synthesis": False,
                        "llm_error": str(e),
                        "raw_results_count": len(relevant_qa),
                        "all_results_shown": True
                    })
                    
                    return error_response, meta
            
            # Store Q&A pair before returning (Strategy 1)
            _store_qa_pair(query, raw_summary, data_source, intent, top_k, similarity_threshold, meta)
            
            return raw_summary, meta
        
        # Strategy 2: If no Q&A pairs found and data provided, do direct semantic search
        if data:
            # Pre-filter data based on query keywords for better results
            filtered_data = _prefilter_data(query, data)
            if filtered_data and len(filtered_data) < len(data):
                # If pre-filtering found matches, use filtered data
                summary, meta, top_results, results_by_type = _direct_semantic_search(query, filtered_data, top_k, similarity_threshold)
                meta["strategy"] = "direct_search_filtered"
                meta["prefiltered_count"] = len(filtered_data)
                meta["original_count"] = len(data)
            else:
                # Otherwise use all data
                summary, meta, top_results, results_by_type = _direct_semantic_search(query, data, top_k, similarity_threshold)
                meta["strategy"] = "direct_search"
            
            # Add LLM synthesis if model and manager are provided
            if llm_model and llm_manager and meta.get("retrieved", 0) > 0:
                try:
                    # Generate insights section
                    insights = _generate_insights(top_results, results_by_type, query)
                    
                    # Create synthesis prompt with direct search results
                    synthesis_prompt = f"""Based on the vector search results, provide a comprehensive and natural answer to the user's question.

User Question: {query}

Vector Search Results:
- Found {meta.get('retrieved', 0)} relevant items from direct search
- Average similarity: {meta.get('avg_similarity', 0):.3f}
- Strategy: {meta.get('strategy', 'unknown')}
- Total candidates searched: {meta.get('total_candidates', 0)}

Search Results:
{summary}

Please provide a clear, well-structured answer that:
1. Summarizes the key findings
2. Lists the most relevant interfaces/items
3. Highlights any important patterns or insights
4. Keeps the answer concise but informative"""

                    # Use the selected LLM model to generate response
                    llm_response = llm_manager.generate_response(
                        model_name=llm_model,
                        system_prompt="You are an expert in integration architecture and API management. Analyze vector search results and provide clear, helpful summaries.",
                        user_prompt=synthesis_prompt
                    )
                    
                    # Combine raw results, insights, and LLM response with clear headings
                    combined_response = f"""# 📊 Vector RAG Analysis Report

## 🔍 Vector Search Results
**Found:** {meta.get('retrieved', 0)} items  
**Strategy:** {meta.get('strategy', 'unknown')}  
**Average Similarity:** {meta.get('avg_similarity', 0) * 100:.1f}%  

{summary}

---

{insights}

---

## 🤖 {llm_model} Response

{llm_response}

---

### 💡 Metadata
- **LLM Model:** {llm_model}
- **Total Candidates Searched:** {meta.get('total_candidates', 0)}
- **Results Retrieved:** {meta.get('retrieved', 0)}
- **Pre-filtered:** {meta.get('prefiltered_count', 'N/A')} from {meta.get('original_count', 'N/A')} total items"""
                    
                    # Update metadata to include LLM usage
                    meta.update({
                        "llm_model_used": llm_model,
                        "llm_synthesis": True,
                        "raw_results_count": meta.get('retrieved', 0),
                        "all_results_shown": True
                    })
                    
                    return combined_response, meta
                    
                except Exception as e:
                    # If LLM synthesis fails, show raw results with error message
                    error_response = f"""# 📊 Vector RAG Analysis Report

## 🔍 Vector Search Results
**Found:** {meta.get('retrieved', 0)} items  
**Strategy:** {meta.get('strategy', 'unknown')}  

{summary}

---

## ⚠️ LLM Synthesis Failed

**Error:** {str(e)}

The raw vector search results are shown above. LLM synthesis could not be completed."""
                    
                    meta.update({
                        "llm_model_used": llm_model,
                        "llm_synthesis": False,
                        "llm_error": str(e),
                        "raw_results_count": meta.get('retrieved', 0),
                        "all_results_shown": True
                    })
                    
                    return error_response, meta
            
            # Store Q&A pair before returning (Strategy 2)
            _store_qa_pair(query, summary, data_source, intent, top_k, similarity_threshold, meta)
            
            return summary, meta
        
        # Strategy 3: No results found
        summary = (
            f"🔍 No relevant results found for query: '{query}'\n\n"
            f"Searched: {data_source} Q&A pairs\n"
            f"Similarity threshold: {similarity_threshold}\n"
            f"Top-k: {top_k}\n\n"
            f"💡 Suggestions:\n"
            f"- Try lowering the similarity threshold\n"
            f"- Try a different data source\n"
            f"- Rephrase your question\n"
        )
        
        meta = {
            "method": "vector_rag",
            "strategy": "no_results",
            "top_k": top_k,
            "retrieved": 0,
            "similarity_threshold": similarity_threshold,
            "data_source": data_source
        }
        
        return summary, meta
        
    except Exception as e:
        # Error handling
        error_summary = (
            f"❌ Vector RAG failed: {str(e)}\n\n"
            f"Query: {query}\n"
            f"Data source: {data_source}\n"
        )
        
        meta = {
            "method": "vector_rag",
            "strategy": "error",
            "error": str(e),
            "top_k": top_k,
            "retrieved": 0
        }
        
        return error_summary, meta


def _prefilter_data(query: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pre-filter data based on query keywords to improve semantic search results.
    
    Args:
        query: User's query
        data: List of data items
    
    Returns:
        Filtered list of data items (or original if no filters match)
    """
    query_lower = query.lower()
    
    # Type-based filtering
    type_keywords = {
        'apim': ['apim', 'api management', 'azure_apim', 'sap_is_apim'],
        'sap': ['sap', 'sap_po', 'sap_pi', 'sap_eventmesh'],
        'azure': ['azure', 'azure_apim'],
        'mule': ['mule', 'mulesoft'],
    }
    
    # Check which type filter to apply
    filter_type = None
    for key, keywords in type_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            filter_type = key
            break
    
    # If a type filter is detected, pre-filter the data
    if filter_type:
        filtered = []
        for item in data:
            item_type = str(item.get('type', '')).lower()
            item_name = str(item.get('name', '')).lower()
            
            # Check metadata for type matches
            metadata_str = ''
            metadata = item.get('metadata', [])
            if isinstance(metadata, list):
                for m in metadata:
                    if isinstance(m, dict):
                        metadata_str += str(m.get('value', '')).lower() + ' '
            
            # Match based on filter type
            if filter_type == 'apim':
                if 'apim' in item_type or 'apim' in item_name or 'apim' in metadata_str:
                    filtered.append(item)
            elif filter_type == 'sap':
                if 'sap' in item_type or 'sap' in item_name:
                    filtered.append(item)
            elif filter_type == 'azure':
                if 'azure' in item_type or 'azure' in item_name:
                    filtered.append(item)
            elif filter_type == 'mule':
                if 'mule' in item_type or 'mule' in item_name:
                    filtered.append(item)
        
        # Return filtered data if we found matches
        if filtered:
            return filtered
    
    # No filters applied or no matches - return original data
    return data


def _generate_insights(results: List[Dict], results_by_type: Dict, query: str) -> str:
    """
    Generate automatic insights from search results.
    
    Args:
        results: List of search results with similarity scores
        results_by_type: Results grouped by type
        query: Original user query
    
    Returns:
        Formatted insights string
    """
    if not results:
        return ""
    
    # Calculate type distribution
    type_counts = {}
    for type_name, type_results in results_by_type.items():
        type_counts[type_name] = len(type_results)
    
    # Sort by count
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    total = len(results)
    
    # Calculate quality distribution
    excellent = len([r for r in results if r['similarity'] >= 0.40])
    good = len([r for r in results if 0.35 <= r['similarity'] < 0.40])
    acceptable = len([r for r in results if 0.30 <= r['similarity'] < 0.35])
    low = len([r for r in results if r['similarity'] < 0.30])
    
    # Get top interface
    top_result = results[0]
    top_name = top_result['item'].get('name', 'N/A')
    top_type = top_result['item'].get('type', 'N/A')
    top_sim = top_result['similarity'] * 100
    
    # Build insights
    insights_parts = [
        f"## 💡 Insights from Results\n",
        f"\n### 📊 Type Distribution\n"
    ]
    
    for type_name, count in sorted_types[:5]:  # Top 5 types
        percentage = (count / total) * 100
        insights_parts.append(f"- **{type_name}**: {count} items ({percentage:.1f}%)\n")
    
    if len(sorted_types) > 5:
        others_count = sum(count for _, count in sorted_types[5:])
        others_pct = (others_count / total) * 100
        insights_parts.append(f"- **Others**: {others_count} items ({others_pct:.1f}%)\n")
    
    insights_parts.append(f"\n### 🎯 Quality Matches\n")
    if excellent > 0:
        insights_parts.append(f"- **Excellent (≥40%)**: {excellent} item{'s' if excellent != 1 else ''} 🔥\n")
    if good > 0:
        insights_parts.append(f"- **Good (35-40%)**: {good} item{'s' if good != 1 else ''} ✅\n")
    if acceptable > 0:
        insights_parts.append(f"- **Acceptable (30-35%)**: {acceptable} item{'s' if acceptable != 1 else ''} 📌\n")
    if low > 0:
        insights_parts.append(f"- **Low (<30%)**: {low} item{'s' if low != 1 else ''}\n")
    
    insights_parts.append(f"\n### 🏆 Top Match\n")
    insights_parts.append(f"**Winner**: `{top_name}` ({top_sim:.1f}% similarity)\n")
    insights_parts.append(f"- **Type**: {top_type}\n")
    
    # Extract sender/receiver if available
    sender = top_result['item'].get('sender', {})
    receiver = top_result['item'].get('receiver', {})
    if isinstance(sender, dict):
        sender = sender.get('name', '')
    if isinstance(receiver, dict):
        receiver = receiver.get('name', '')
    
    if sender:
        insights_parts.append(f"- **Sender**: {sender}\n")
    if receiver:
        insights_parts.append(f"- **Receiver**: {receiver}\n")
    
    return "".join(insights_parts)


def _direct_semantic_search(query: str, data: List[Dict[str, Any]], 
                            top_k: int, similarity_threshold: float) -> tuple[str, Dict[str, Any], List, Dict]:
    """
    Perform direct semantic search on provided data using embeddings.
    
    Args:
        query: The user query
        data: List of data items to search
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score
    
    Returns:
        summary: Formatted results
        meta: Metadata
    """
    try:
        # Initialize embedding model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Generate query embedding
        query_embedding = model.encode(query)
        
        # Generate embeddings for data items and calculate similarities
        results = []
        for item in data:
            # Create searchable text from item
            item_text = _create_searchable_text(item)
            item_embedding = model.encode(item_text)
            
            # Calculate cosine similarity
            similarity = _cosine_similarity(query_embedding, item_embedding)
            
            if similarity >= similarity_threshold:
                results.append({
                    "item": item,
                    "text": item_text,
                    "similarity": similarity
                })
        
        # Sort by similarity and take top-k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        top_results = results[:top_k]
        
        if top_results:
            # Create organized summary with statistics
            summary_parts = [
                f"### 📊 Vector Search Statistics\n",
                f"- **Total Results Found:** {len(top_results)}\n",
                f"- **Average Similarity:** {sum(r['similarity'] for r in top_results) / len(top_results) * 100:.1f}%\n",
                f"- **Similarity Range:** {top_results[0]['similarity'] * 100:.1f}% - {top_results[-1]['similarity'] * 100:.1f}%\n",
                f"- **Threshold Applied:** {similarity_threshold * 100:.0f}%\n",
                f"\n---\n",
                f"\n### 🔍 Search Results\n"
            ]
            
            # Group results by type for better organization
            results_by_type = {}
            for result in top_results:
                item = result['item']
                item_type = str(item.get('type', 'Unknown'))
                if item_type not in results_by_type:
                    results_by_type[item_type] = []
                results_by_type[item_type].append(result)
            
            # Show top 20 results in detail, then summary by type
            detailed_count = min(20, len(top_results))
            
            summary_parts.append(f"\n#### Top {detailed_count} Results (Detailed View)\n")
            
            for i, result in enumerate(top_results[:detailed_count], 1):
                similarity = result['similarity'] * 100
                item = result['item']
                
                # Format item details
                name = item.get('name') or item.get('inv_name', 'N/A')
                item_type = item.get('type', 'N/A')
                description = item.get('description', '')
                
                # Extract sender/receiver if available
                sender = item.get('sender', {})
                receiver = item.get('receiver', {})
                if isinstance(sender, dict):
                    sender = sender.get('name', '')
                if isinstance(receiver, dict):
                    receiver = receiver.get('name', '')
                
                sender_receiver_info = ""
                if sender:
                    sender_receiver_info += f"**Sender:** {sender}\n"
                if receiver:
                    sender_receiver_info += f"**Receiver:** {receiver}\n"
                
                summary_parts.append(
                    f"\n**#{i}** - Similarity: **{similarity:.1f}%** {'🔥' if similarity >= 40 else '✅' if similarity >= 35 else '📌'}\n"
                    f"```\n"
                    f"Name: {name}\n"
                    f"Type: {item_type}\n"
                    f"{sender_receiver_info}"
                    f"{'Description: ' + description[:150] + '...' if description and len(description) > 150 else 'Description: ' + description if description else ''}\n"
                    f"```\n"
                )
            
            # Add summary by type if there are more than 20 results
            if len(top_results) > detailed_count:
                summary_parts.append(f"\n---\n\n#### 📋 Remaining {len(top_results) - detailed_count} Results (Summary by Type)\n")
                
                for type_name, type_results in sorted(results_by_type.items(), key=lambda x: len(x[1]), reverse=True):
                    count = len(type_results)
                    avg_sim = sum(r['similarity'] for r in type_results) / count * 100
                    
                    # Show count for this type if we already showed some in detail
                    shown_in_detail = len([r for r in type_results if top_results.index(r) < detailed_count])
                    remaining = count - shown_in_detail
                    
                    if remaining > 0:
                        summary_parts.append(
                            f"\n**Type: {type_name}** - {remaining} more item{'s' if remaining > 1 else ''} (Avg Similarity: {avg_sim:.1f}%)\n"
                        )
                        
                        # Show names of remaining items (up to 5 per type)
                        remaining_items = [r for r in type_results if top_results.index(r) >= detailed_count][:5]
                        for result in remaining_items:
                            name = result['item'].get('name', 'N/A')
                            sim = result['similarity'] * 100
                            summary_parts.append(f"  • {name} ({sim:.1f}%)\n")
                        
                        if len([r for r in type_results if top_results.index(r) >= detailed_count]) > 5:
                            summary_parts.append(f"  • ... and {len([r for r in type_results if top_results.index(r) >= detailed_count]) - 5} more\n")
            
            summary = "".join(summary_parts)
            
            meta = {
                "method": "vector_rag",
                "retrieved": len(top_results),
                "total_candidates": len(data),
                "avg_similarity": sum(r['similarity'] for r in top_results) / len(top_results)
            }
            
            return summary, meta, top_results, results_by_type
        else:
            summary = f"🔍 No items found with similarity >= {similarity_threshold}"
            meta = {
                "method": "vector_rag",
                "retrieved": 0,
                "total_candidates": len(data)
            }
            return summary, meta, [], {}
            
    except Exception as e:
        error_summary = f"❌ Direct semantic search failed: {str(e)}"
        meta = {
            "method": "vector_rag",
            "error": str(e),
            "retrieved": 0
        }
        return error_summary, meta, [], {}


def _create_searchable_text(item: Dict[str, Any]) -> str:
    """Create searchable text from a data item."""
    parts = []
    
    # Add name/title
    name = item.get('name') or item.get('inv_name', '')
    if name:
        parts.append(f"Name: {name}")
    
    # Add type (convert to string to handle both string and numeric types)
    item_type = item.get('type', '')
    if item_type:
        parts.append(f"Type: {str(item_type)}")
    
    # Add description
    description = item.get('description', '')
    if description:
        parts.append(f"Description: {description}")
    
    # Add sender/receiver info
    # Handle both 'sender_name' (string) and 'sender' (dict with 'name' key)
    sender = item.get('sender_name', '') or item.get('sender', '')
    if isinstance(sender, dict):
        sender = sender.get('name', '')
    if sender:
        parts.append(f"Sender: {sender}")
    
    # Handle both 'receiver_name' (string) and 'receiver' (dict with 'name' key)
    receiver = item.get('receiver_name', '') or item.get('receiver', '')
    if isinstance(receiver, dict):
        receiver = receiver.get('name', '')
    if receiver:
        parts.append(f"Receiver: {receiver}")
    
    # Add metadata array (common in your JSON structure)
    metadata = item.get('metadata', [])
    if metadata and isinstance(metadata, list):
        metadata_texts = []
        for meta_item in metadata[:10]:  # Limit to first 10 metadata items
            if isinstance(meta_item, dict):
                meta_name = meta_item.get('name', '')
                meta_value = meta_item.get('value', '')
                if meta_name and meta_value:
                    metadata_texts.append(f"{meta_name}: {meta_value}")
        if metadata_texts:
            parts.append(" | ".join(metadata_texts))
    
    # Add tags
    tags = item.get('tags', [])
    if tags:
        tag_names = []
        for t in tags:
            if isinstance(t, dict):
                # Handle nested tag structure: {"value": "...", "tag": {"name": "..."}}
                tag_value = t.get('tag', '')
                if isinstance(tag_value, dict):
                    # Extract the 'name' from nested dict
                    tag_names.append(tag_value.get('name', ''))
                elif tag_value:
                    tag_names.append(str(tag_value))
                # Also include the 'value' field if present
                tag_val = t.get('value', '')
                if tag_val:
                    tag_names.append(str(tag_val))
            else:
                tag_names.append(str(t))
        # Filter out empty strings
        tag_names = [name for name in tag_names if name]
        if tag_names:
            parts.append(f"Tags: {', '.join(tag_names)}")
    
    return " | ".join(parts)


def _cosine_similarity(vec1, vec2) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    
    # Normalize vectors
    vec1_norm = vec1 / np.linalg.norm(vec1)
    vec2_norm = vec2 / np.linalg.norm(vec2)
    
    # Calculate cosine similarity
    similarity = np.dot(vec1_norm, vec2_norm)
    
    return float(similarity) 