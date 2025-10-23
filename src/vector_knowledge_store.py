"""
Module: vector_knowledge_store

Purpose:
    Manage question/answer pairs in a persistent ChromaDB vector store to
    enable semantic search, reuse of prior answers, and analytics on intents
    and entities.

Key Concepts:
    - Two collections: `duckdb_qa_pairs` and `api_qa_pairs`
    - Lightweight entity extraction from response data for metadata enrichment
    - Simple response-type detection for downstream ranking/UX

Public API:
    - `VectorKnowledgeStore`: store Q&A pairs, search similar QAs, get stats

Inputs/Outputs:
    - Inputs: Question text, answer text, query dict, endpoint, intent, source
    - Outputs: Stored vectors with rich metadata, search results, recent items

Dependencies:
    - External: `chromadb`, `sentence_transformers`

Usage:
    >>> vks = VectorKnowledgeStore()
    >>> qa_id = vks.store_qa_pair(question, answer, query, endpoint, intent, "duckdb")
    >>> sims = vks.find_similar_qa(question, data_source="duckdb", top_k=5)
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class VectorKnowledgeStore:
    """Manages Q&A pairs in ChromaDB with semantic search capabilities."""
    
    def __init__(self, vector_dir: str = "vector_store"):
        self.vector_dir = Path(vector_dir)
        self.vector_dir.mkdir(exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.vector_dir / "chroma_db"),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collections
        self.duckdb_collection = self._get_or_create_collection("duckdb_qa_pairs")
        self.api_collection = self._get_or_create_collection("api_qa_pairs")
        
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                metadata={"description": f"Q&A pairs from {name.split('_')[0]} source"}
            )
    
    def _generate_qa_id(self, question: str, query: Dict[str, Any], endpoint: str) -> str:
        """Generate unique ID for Q&A pair."""
        content = f"{question}_{json.dumps(query, sort_keys=True)}_{endpoint}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _extract_entities(self, response_data: Dict[str, Any]) -> List[str]:
        """Extract entity names from response data."""
        entities = []
        if isinstance(response_data, dict) and 'data' in response_data:
            for item in response_data['data'][:10]:  # Limit to first 10 for performance
                if isinstance(item, dict):
                    name = item.get('name') or item.get('norm_name')
                    if name:
                        entities.append(name)
        return entities[:5]  # Return max 5 entities
    
    def _detect_response_type(self, answer: str) -> str:
        """Detect the type of response based on content."""
        answer_lower = answer.lower()
        if "complete list" in answer_lower or "total:" in answer_lower:
            return "direct_list"
        elif "count results" in answer_lower or "total:" in answer_lower:
            return "count_response"
        elif "search results" in answer_lower or "found" in answer_lower:
            return "search_response"
        elif "analysis" in answer_lower or "insights" in answer_lower:
            return "analysis_response"
        else:
            return "general_response"
    
    def store_qa_pair(self, question: str, answer: str, query: Dict[str, Any], 
                     endpoint: str, intent: str, data_source: str = "duckdb",
                     response_data: Optional[Dict[str, Any]] = None,
                     sql_query: Optional[str] = None,
                     method: Optional[str] = None,
                     top_k: Optional[int] = None,
                     similarity_threshold: Optional[float] = None,
                     extra_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a Q&A pair in the appropriate collection.
        
        Args:
            question: User's question
            answer: Generated answer
            query: WHINT API query or empty dict for vector searches
            endpoint: API endpoint used or "local_json" for local files
            intent: Detected intent (list_all, count, search, analyze, api, etc.)
            data_source: Source of data (duckdb, api, local_json)
            response_data: Raw response data for entity extraction
            sql_query: SQL query used (for DuckDB)
            method: Method used (vector_rag, graph_rag, db_lookup, etc.)
            top_k: Number of top results retrieved
            similarity_threshold: Similarity threshold used
            extra_metadata: Additional metadata to store
            
        Returns:
            Q&A pair ID
        """
        try:
            # Generate unique ID
            qa_id = self._generate_qa_id(question, query, endpoint)
            
            # Create document for embedding
            document = f"Question: {question}\nAnswer: {answer}"
            
            # Extract entities if response data provided
            entities = []
            if response_data:
                entities = self._extract_entities(response_data)
            
            # Prepare metadata
            metadata = {
                "intent": intent,
                "endpoint": endpoint,
                "data_source": data_source,
                "query_hash": hashlib.md5(json.dumps(query, sort_keys=True).encode()).hexdigest()[:16],
                "entity": query.get('query', {}).get('entity', 'unknown'),
                "response_type": self._detect_response_type(answer),
                "entities": json.dumps(entities),
                "timestamp": datetime.now().isoformat(),
                "total_items": len(response_data.get('data', [])) if response_data else 0
            }
            
            # Add method-specific metadata (for vector_rag, graph_rag, etc.)
            if method:
                metadata["method"] = method
            if top_k is not None:
                metadata["top_k"] = str(top_k)  # Convert to string for ChromaDB compatibility
            if similarity_threshold is not None:
                metadata["similarity_threshold"] = str(similarity_threshold)
            
            # Add any extra metadata passed in
            if extra_metadata:
                for key, value in extra_metadata.items():
                    # Convert non-string values to strings for ChromaDB
                    metadata[key] = str(value) if not isinstance(value, str) else value
            
            # Add SQL query for DuckDB responses
            if sql_query:
                metadata["sql_query"] = sql_query[:500]  # Truncate for storage
            
            # Choose collection based on data source
            # Use duckdb_collection for local_json since it's similar to duckdb (local processing)
            if data_source in ["duckdb", "local_json"]:
                collection = self.duckdb_collection
            else:
                collection = self.api_collection
            
            # Store in ChromaDB
            collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[qa_id]
            )
            
            return qa_id
            
        except Exception as e:
            print(f"Warning: Could not store Q&A pair in vector store: {e}")
            return ""
    
    def find_similar_qa(self, question: str, data_source: str = "duckdb", 
                       intent: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar Q&A pairs using semantic search.
        
        Args:
            question: User's question
            data_source: Source to search (duckdb, api, or both)
            intent: Filter by intent type
            top_k: Number of results to return
            
        Returns:
            List of similar Q&A pairs with metadata
        """
        try:
            # Choose collection based on data source
            if data_source in ["duckdb", "local_json"]:
                collection = self.duckdb_collection
            elif data_source == "api":
                collection = self.api_collection
            else:
                # Search both collections
                results = []
                for coll in [self.duckdb_collection, self.api_collection]:
                    coll_results = self._search_collection(coll, question, intent, top_k)
                    results.extend(coll_results)
                # Sort by distance and return top_k
                results.sort(key=lambda x: x['distance'])
                return results[:top_k]
            
            return self._search_collection(collection, question, intent, top_k)
            
        except Exception as e:
            print(f"Warning: Could not search vector store: {e}")
            return []
    
    def _search_collection(self, collection, question: str, intent: Optional[str], top_k: int) -> List[Dict[str, Any]]:
        """Search a specific collection."""
        try:
            # Prepare where clause for filtering
            where_clause = {}
            if intent:
                where_clause["intent"] = intent
            
            # Perform similarity search
            results = collection.query(
                query_texts=[question],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'question': self._extract_question_from_doc(doc),
                        'answer': self._extract_answer_from_doc(doc),
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'similarity': 1 - (results['distances'][0][i] if results['distances'] else 0.0)
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Warning: Could not search collection: {e}")
            return []
    
    def _extract_question_from_doc(self, document: str) -> str:
        """Extract question from document."""
        if "Question:" in document:
            return document.split("Question:")[1].split("Answer:")[0].strip()
        return document[:100] + "..." if len(document) > 100 else document
    
    def _extract_answer_from_doc(self, document: str) -> str:
        """Extract answer from document."""
        if "Answer:" in document:
            return document.split("Answer:")[1].strip()
        return document
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about stored Q&A pairs."""
        try:
            duckdb_count = self.duckdb_collection.count()
            api_count = self.api_collection.count()
            
            return {
                "duckdb_qa_pairs": duckdb_count,
                "api_qa_pairs": api_count,
                "total_qa_pairs": duckdb_count + api_count,
                "vector_store_path": str(self.vector_dir)
            }
        except Exception as e:
            print(f"Warning: Could not get collection stats: {e}")
            return {"error": str(e)}
    
    def get_recent_qa_pairs(self, data_source: str = "duckdb", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent Q&A pairs for display."""
        try:
            if data_source in ["duckdb", "local_json"]:
                collection = self.duckdb_collection
            else:
                collection = self.api_collection
            
            # Get all documents (this is a simple approach, could be optimized)
            results = collection.get()
            
            if not results['documents']:
                return []
            
            # Format and sort by timestamp
            qa_pairs = []
            for i, doc in enumerate(results['documents']):
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                qa_pairs.append({
                    'question': self._extract_question_from_doc(doc),
                    'answer': self._extract_answer_from_doc(doc)[:200] + "...",
                    'metadata': metadata,
                    'timestamp': metadata.get('timestamp', '')
                })
            
            # Sort by timestamp (newest first)
            qa_pairs.sort(key=lambda x: x['timestamp'], reverse=True)
            return qa_pairs[:limit]
            
        except Exception as e:
            print(f"Warning: Could not get recent Q&A pairs: {e}")
            return []
    
    def clear_collection(self, data_source: str = "duckdb"):
        """Clear all Q&A pairs from a collection (for testing)."""
        try:
            if data_source == "duckdb":
                self.client.delete_collection("duckdb_qa_pairs")
                self.duckdb_collection = self._get_or_create_collection("duckdb_qa_pairs")
            elif data_source == "api":
                self.client.delete_collection("api_qa_pairs")
                self.api_collection = self._get_or_create_collection("api_qa_pairs")
        except Exception as e:
            print(f"Warning: Could not clear collection: {e}")
