#!/usr/bin/env python3
"""
Test script to demonstrate vector store retrieval methods
"""

from src.vector_knowledge_store import VectorKnowledgeStore

def test_vector_retrieval():
    """Test various vector store retrieval methods"""
    print("🔍 Testing Vector Store Retrieval Methods")
    print("=" * 50)
    
    # Initialize vector store
    vs = VectorKnowledgeStore()
    
    # Method 1: Similarity Search
    print("\n1. SIMILARITY SEARCH")
    print("-" * 20)
    similar = vs.find_similar_qa('list all interfaces', data_source='duckdb', top_k=3)
    if similar:
        for i, qa in enumerate(similar):
            print(f"{i+1}. Question: {qa['question']}")
            print(f"   Similarity: {qa['similarity']:.1%}")
            print(f"   Answer: {qa['answer'][:100]}...")
            print()
    else:
        print("No similar questions found.")
    
    # Method 2: Recent Q&A Pairs
    print("\n2. RECENT Q&A PAIRS")
    print("-" * 20)
    recent = vs.get_recent_qa_pairs('duckdb', limit=5)
    if recent:
        for i, qa in enumerate(recent):
            print(f"{i+1}. Question: {qa['question']}")
            print(f"   Answer: {qa['answer'][:100]}...")
            print(f"   Timestamp: {qa.get('timestamp', 'N/A')}")
            print()
    else:
        print("No Q&A pairs found.")
    
    # Method 3: Collection Statistics
    print("\n3. COLLECTION STATISTICS")
    print("-" * 20)
    stats = vs.get_collection_stats()
    print(f"DuckDB Q&A pairs: {stats.get('duckdb_qa_pairs', 0)}")
    print(f"API Q&A pairs: {stats.get('api_qa_pairs', 0)}")
    print(f"Total Q&A pairs: {stats.get('total_qa_pairs', 0)}")
    print(f"Vector store path: {stats.get('vector_store_path', 'N/A')}")
    
    # Method 4: Intent-based Search
    print("\n4. INTENT-BASED SEARCH")
    print("-" * 20)
    intent_results = vs.find_similar_qa('count interfaces', data_source='duckdb', intent='count', top_k=2)
    if intent_results:
        for i, qa in enumerate(intent_results):
            print(f"{i+1}. Question: {qa['question']}")
            print(f"   Intent: {qa.get('metadata', {}).get('intent', 'N/A')}")
            print(f"   Similarity: {qa['similarity']:.1%}")
            print()
    else:
        print("No questions found for 'count' intent.")

if __name__ == "__main__":
    test_vector_retrieval()

