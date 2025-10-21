"""
Tree-based (hierarchical) summarization method.
Recursively summarizes data in token-bounded chunks, then summarizes the summaries.

This method implements a hierarchical summarization strategy that:
1. Splits data into token-bounded chunks
2. Summarizes each chunk using an LLM
3. Recursively merges summaries until a single summary remains
4. Ensures token limits are respected at each level
"""

import json
from typing import Dict, List, Any, Optional
from src.llm_providers import LLMProviderManager


def run(query: str, data: List[Dict[str, Any]], 
        max_tokens_per_chunk: int = 3000,
        max_tokens_per_summary: int = 500,
        llm_manager: Optional[LLMProviderManager] = None,
        llm_model: Optional[str] = None,
        **kwargs) -> tuple[str, Dict[str, Any]]:
    """
    Hierarchical tree summarization with token-bounded recursive merges.
    
    This method performs hierarchical summarization by:
    1. Chunking data based on token limits
    2. Summarizing each chunk
    3. Recursively merging summaries until one remains
    
    Args:
        query: The user query or prompt
        data: List of data items to summarize
        max_tokens_per_chunk: Maximum tokens per chunk (default: 3000)
        max_tokens_per_summary: Maximum tokens for each summary (default: 500)
        llm_manager: LLM provider manager (optional, will create if not provided)
        llm_model: Specific LLM model to use (optional)
        **kwargs: Additional parameters
    
    Returns:
        summary: The final hierarchical summary
        meta: Metadata about the summarization process
    """
    try:
        # Initialize LLM manager if not provided
        if llm_manager is None:
            llm_manager = LLMProviderManager()
        
        # Select model if not provided
        if llm_model is None:
            available_models = llm_manager.get_available_models()
            if not available_models:
                return _fallback_summary(query, data, "No LLM models available")
            llm_model = available_models[0]
        
        # Convert data to text chunks
        text_chunks = _create_text_chunks(data, max_tokens_per_chunk)
        
        if not text_chunks:
            return _fallback_summary(query, data, "No data to summarize")
        
        # Track metadata
        total_chunks = len(text_chunks)
        levels = 0
        summaries_generated = 0
        
        # Level 1: Summarize each chunk
        level_summaries = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_summary = _summarize_chunk(
                query, chunk_text, i + 1, total_chunks,
                llm_manager, llm_model, max_tokens_per_summary
            )
            level_summaries.append(chunk_summary)
            summaries_generated += 1
        
        levels += 1
        
        # Recursive merging: Keep merging until we have one summary
        while len(level_summaries) > 1:
            levels += 1
            next_level_summaries = []
            
            # Group summaries into chunks for merging
            merge_chunks = _create_summary_chunks(level_summaries, max_tokens_per_chunk)
            
            for i, summary_chunk in enumerate(merge_chunks):
                merged_summary = _merge_summaries(
                    query, summary_chunk, i + 1, len(merge_chunks),
                    llm_manager, llm_model, max_tokens_per_summary
                )
                next_level_summaries.append(merged_summary)
                summaries_generated += 1
            
            level_summaries = next_level_summaries
        
        # Final summary
        final_summary = level_summaries[0] if level_summaries else "No summary generated"
        
        meta = {
            "method": "tree_summarization",
            "strategy": "token_bounded_recursive",
            "total_items": len(data),
            "total_chunks": total_chunks,
            "levels": levels,
            "summaries_generated": summaries_generated,
            "max_tokens_per_chunk": max_tokens_per_chunk,
            "max_tokens_per_summary": max_tokens_per_summary,
            "llm_model": llm_model
        }
        
        return final_summary, meta
        
    except Exception as e:
        return _fallback_summary(query, data, f"Error: {str(e)}")


def _create_text_chunks(data: List[Dict[str, Any]], max_tokens: int) -> List[str]:
    """
    Create text chunks from data items, respecting token limits.
    
    Args:
        data: List of data items
        max_tokens: Maximum tokens per chunk
    
    Returns:
        List of text chunks
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for item in data:
        # Convert item to text
        item_text = _item_to_text(item)
        item_tokens = _estimate_tokens(item_text)
        
        # Check if adding this item would exceed limit
        if current_tokens + item_tokens > max_tokens and current_chunk:
            # Save current chunk and start new one
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [item_text]
            current_tokens = item_tokens
        else:
            current_chunk.append(item_text)
            current_tokens += item_tokens
    
    # Add remaining chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def _create_summary_chunks(summaries: List[str], max_tokens: int) -> List[List[str]]:
    """
    Group summaries into chunks for merging.
    
    Args:
        summaries: List of summary strings
        max_tokens: Maximum tokens per chunk
    
    Returns:
        List of summary chunks
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for summary in summaries:
        summary_tokens = _estimate_tokens(summary)
        
        if current_tokens + summary_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [summary]
            current_tokens = summary_tokens
        else:
            current_chunk.append(summary)
            current_tokens += summary_tokens
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def _summarize_chunk(query: str, chunk_text: str, chunk_num: int, total_chunks: int,
                     llm_manager: LLMProviderManager, llm_model: str,
                     max_tokens: int) -> str:
    """Summarize a single chunk of data."""
    system_prompt = f"""You are an expert at summarizing technical data about system interfaces.
Your task is to create a concise, informative summary of the provided data chunk.

Focus on:
- Key interface names and types
- Important patterns or trends
- Sender/receiver relationships
- Notable properties or metadata

Keep the summary under {max_tokens} tokens."""
    
    user_prompt = f"""User Query: {query}

Data Chunk {chunk_num} of {total_chunks}:
{chunk_text}

Provide a concise summary of this data chunk that addresses the user's query."""
    
    try:
        response = llm_manager.generate_response(
            model_name=llm_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=max_tokens
        )
        return response if response else f"[Summary of chunk {chunk_num} unavailable]"
    except Exception as e:
        return f"[Error summarizing chunk {chunk_num}: {str(e)}]"


def _merge_summaries(query: str, summaries: List[str], merge_num: int, total_merges: int,
                     llm_manager: LLMProviderManager, llm_model: str,
                     max_tokens: int) -> str:
    """Merge multiple summaries into one."""
    system_prompt = f"""You are an expert at synthesizing multiple summaries into a coherent whole.
Your task is to merge the provided summaries into a single, comprehensive summary.

Focus on:
- Combining key insights from all summaries
- Eliminating redundancy
- Maintaining important details
- Creating a coherent narrative

Keep the merged summary under {max_tokens} tokens."""
    
    summaries_text = "\n\n---\n\n".join([f"Summary {i+1}:\n{s}" for i, s in enumerate(summaries)])
    
    user_prompt = f"""User Query: {query}

Merge Group {merge_num} of {total_merges}:
{summaries_text}

Merge these summaries into a single, comprehensive summary that addresses the user's query."""
    
    try:
        response = llm_manager.generate_response(
            model_name=llm_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=max_tokens
        )
        return response if response else f"[Merged summary {merge_num} unavailable]"
    except Exception as e:
        return f"[Error merging summaries {merge_num}: {str(e)}]"


def _item_to_text(item: Dict[str, Any]) -> str:
    """Convert a data item to text representation."""
    parts = []
    
    # Add name
    name = item.get('name') or item.get('inv_name', 'Unknown')
    parts.append(f"Interface: {name}")
    
    # Add type
    item_type = item.get('type', 'N/A')
    parts.append(f"Type: {item_type}")
    
    # Add sender/receiver
    sender = item.get('sender_name', 'N/A')
    receiver = item.get('receiver_name', 'N/A')
    parts.append(f"Sender: {sender} → Receiver: {receiver}")
    
    # Add description if available
    description = item.get('description', '')
    if description:
        parts.append(f"Description: {description[:200]}")
    
    # Add tags if available
    tags = item.get('tags', [])
    if tags:
        tag_names = [t.get('tag', '') if isinstance(t, dict) else str(t) for t in tags[:5]]
        parts.append(f"Tags: {', '.join(tag_names)}")
    
    return " | ".join(parts)


def _estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ≈ 4 characters)."""
    return len(text) // 4


def _fallback_summary(query: str, data: List[Dict[str, Any]], reason: str) -> tuple[str, Dict[str, Any]]:
    """Generate a fallback summary when LLM is unavailable."""
    summary = f"""🔄 Tree Summarization (Fallback Mode)

Query: {query}
Reason: {reason}

Basic Statistics:
- Total items: {len(data)}
- Item types: {_get_type_distribution(data)}

Note: Full hierarchical summarization requires an LLM. Using basic statistics instead."""
    
    meta = {
        "method": "tree_summarization",
        "strategy": "fallback",
        "total_items": len(data),
        "reason": reason
    }
    
    return summary, meta


def _get_type_distribution(data: List[Dict[str, Any]]) -> str:
    """Get distribution of types in data."""
    type_counts = {}
    for item in data:
        item_type = item.get('type', 'Unknown')
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
    
    return ", ".join([f"{t}: {c}" for t, c in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]]) 