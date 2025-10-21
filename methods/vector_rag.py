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


def run(query: str, data: Optional[List[Dict[str, Any]]] = None, top_k: int = 5, 
        data_source: str = "duckdb", intent: Optional[str] = None, 
        similarity_threshold: float = 0.7, **kwargs) -> tuple[str, Dict[str, Any]]:
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
        
        # Strategy 1: Search stored Q&A pairs first
        similar_qa = vector_store.find_similar_qa(
            question=query,
            data_source=data_source,
            intent=intent,
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
            
            summary = "\n".join(summary_parts)
            
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
            
            return summary, meta
        
        # Strategy 2: If no Q&A pairs found and data provided, do direct semantic search
        if data:
            summary, meta = _direct_semantic_search(query, data, top_k, similarity_threshold)
            meta["strategy"] = "direct_search"
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


def _direct_semantic_search(query: str, data: List[Dict[str, Any]], 
                            top_k: int, similarity_threshold: float) -> tuple[str, Dict[str, Any]]:
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
            summary_parts = [
                f"🔍 Found {len(top_results)} relevant items from direct search:\n"
            ]
            
            for i, result in enumerate(top_results, 1):
                similarity = result['similarity'] * 100
                item = result['item']
                
                # Format item details
                name = item.get('name') or item.get('inv_name', 'N/A')
                item_type = item.get('type', 'N/A')
                description = item.get('description', '')
                
                summary_parts.append(
                    f"\n**Result {i}** (Similarity: {similarity:.1f}%)\n"
                    f"**Name:** {name}\n"
                    f"**Type:** {item_type}\n"
                    f"**Description:** {description[:200]}{'...' if len(description) > 200 else ''}\n"
                )
            
            summary = "\n".join(summary_parts)
            
            meta = {
                "method": "vector_rag",
                "retrieved": len(top_results),
                "total_candidates": len(data),
                "avg_similarity": sum(r['similarity'] for r in top_results) / len(top_results)
            }
            
            return summary, meta
        else:
            summary = f"🔍 No items found with similarity >= {similarity_threshold}"
            meta = {
                "method": "vector_rag",
                "retrieved": 0,
                "total_candidates": len(data)
            }
            return summary, meta
            
    except Exception as e:
        error_summary = f"❌ Direct semantic search failed: {str(e)}"
        meta = {
            "method": "vector_rag",
            "error": str(e),
            "retrieved": 0
        }
        return error_summary, meta


def _create_searchable_text(item: Dict[str, Any]) -> str:
    """Create searchable text from a data item."""
    parts = []
    
    # Add name/title
    name = item.get('name') or item.get('inv_name', '')
    if name:
        parts.append(f"Name: {name}")
    
    # Add type
    item_type = item.get('type', '')
    if item_type:
        parts.append(f"Type: {item_type}")
    
    # Add description
    description = item.get('description', '')
    if description:
        parts.append(f"Description: {description}")
    
    # Add sender/receiver info
    sender = item.get('sender_name', '')
    if sender:
        parts.append(f"Sender: {sender}")
    
    receiver = item.get('receiver_name', '')
    if receiver:
        parts.append(f"Receiver: {receiver}")
    
    # Add tags
    tags = item.get('tags', [])
    if tags:
        tag_names = [t.get('tag', '') if isinstance(t, dict) else str(t) for t in tags]
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