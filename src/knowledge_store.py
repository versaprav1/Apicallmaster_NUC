"""
Module: knowledge_store

Purpose:
    Cache and reuse processed API responses and derived summaries to reduce
    repeated computation and network usage. Provides index-based lookup,
    fuzzy matching for similar queries, and a persistent entity string log.

Key Concepts:
    - Normalized cache keys derived from queries and endpoints
    - TTL-based validity and index maintenance
    - Fuzzy reuse of similar queries when exact match is absent
    - Persistent per-endpoint entity string logs for downstream analysis

Public API:
    - `KnowledgeStore`: manage storage, retrieval, search, and cleanup

Inputs/Outputs:
    - Inputs: Query dicts and endpoint strings, raw API responses, summaries
    - Outputs: Cached JSON files and index metadata; optional entity JSONL logs

Dependencies:
    - External: Standard library only (json, hashlib, datetime, pathlib)

Usage:
    >>> ks = KnowledgeStore()
    >>> key = ks.store_response(query, endpoint, raw, summary)
    >>> cached = ks.get_cached_response(query, endpoint)
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path


class KnowledgeStore:
    """Manages cached knowledge from processed API responses"""
    
    def __init__(self, cache_dir: str = "knowledge_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.max_age_days = 30  # Cache expires after 30 days (extended from 7)
        
        # NEW: persistent entity store directory (separate from cache)
        self.entity_store_dir = Path("knowledge_entities")
        self.entity_store_dir.mkdir(exist_ok=True)
        
        # Load existing index
        self.index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the cache index"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_index(self):
        """Save the cache index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache index: {e}")
    
    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize query for better cache matching"""
        if not isinstance(query, dict):
            return query
        
        normalized = {}
        for key, value in query.items():
            if key == 'query' and isinstance(value, dict):
                # Normalize the nested query structure
                normalized_query = {}
                for q_key, q_value in value.items():
                    if q_key == 'fields' and isinstance(q_value, list):
                        # Sort fields for consistent ordering
                        normalized_query[q_key] = sorted(q_value)
                    elif q_key == 'where' and isinstance(q_value, list):
                        # Normalize where conditions
                        normalized_where = []
                        for condition in q_value:
                            if isinstance(condition, dict):
                                normalized_condition = {}
                                for c_key, c_value in condition.items():
                                    if c_key == 'conditions' and isinstance(c_value, list):
                                        # Sort conditions for consistency
                                        normalized_condition[c_key] = sorted(c_value, key=lambda x: json.dumps(x, sort_keys=True))
                                    else:
                                        normalized_condition[c_key] = c_value
                                normalized_where.append(normalized_condition)
                        normalized_query[q_key] = normalized_where
                    else:
                        normalized_query[q_key] = q_value
                normalized[key] = normalized_query
            else:
                normalized[key] = value
        
        return normalized
    
    def _generate_cache_key(self, query: Dict[str, Any], endpoint: str) -> str:
        """Generate a unique cache key for a query with improved normalization"""
        # Normalize query for better matching
        normalized_query = self._normalize_query(query)
        query_str = json.dumps(normalized_query, sort_keys=True)
        cache_input = f"{endpoint}:{query_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is still valid"""
        try:
            created_time = datetime.fromisoformat(cache_entry['created_at'])
            age = datetime.now() - created_time
            return age.days < self.max_age_days
        except Exception:
            return False
    
    def get_cached_response(self, query: Dict[str, Any], endpoint: str, debug: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available and valid"""
        cache_key = self._generate_cache_key(query, endpoint)
        
        if debug:
            print(f"🔍 Cache Debug - Generated key: {cache_key}")
            print(f"🔍 Cache Debug - Query: {json.dumps(query, indent=2)}")
            print(f"🔍 Cache Debug - Endpoint: {endpoint}")
            print(f"🔍 Cache Debug - Index has {len(self.index)} entries")
        
        if cache_key in self.index:
            cache_entry = self.index[cache_key]
            
            if debug:
                print(f"🔍 Cache Debug - Found entry: {cache_entry}")
            
            if self._is_cache_valid(cache_entry):
                # Load the cached data
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r') as f:
                            cached_data = json.load(f)
                        
                        # Update last accessed time
                        cache_entry['last_accessed'] = datetime.now().isoformat()
                        self._save_index()
                        
                        if debug:
                            print(f"✅ Cache Debug - Cache HIT! Returning cached data")
                        
                        return cached_data
                    except Exception as e:
                        print(f"Warning: Could not load cached data: {e}")
                        # Remove invalid cache entry
                        self._remove_cache_entry(cache_key)
            else:
                if debug:
                    print(f"❌ Cache Debug - Entry expired, removing")
                # Remove expired cache entry
                self._remove_cache_entry(cache_key)
        else:
            if debug:
                print(f"❌ Cache Debug - Cache MISS - Key not found in index")
        
        return None
    
    def store_response(self, query: Dict[str, Any], endpoint: str, 
                      raw_response: Dict[str, Any], processed_summary: str,
                      chunk_summaries: Optional[List[str]] = None) -> str:
        """Store a processed response in cache"""
        cache_key = self._generate_cache_key(query, endpoint)
        
        # Prepare cache data
        entity_strings = self._extract_entity_strings(raw_response)
        # Persistently append entity strings outside cache as well
        try:
            self.append_entity_strings_persistent(endpoint, entity_strings)
        except Exception:
            pass
        cache_data = {
            "query": query,
            "endpoint": endpoint,
            "raw_response_summary": {
                "total_items": len(raw_response.get('data', [])) if isinstance(raw_response, dict) and isinstance(raw_response.get('data'), list) else (len(raw_response) if isinstance(raw_response, list) else 0),
                "response_size_chars": len(json.dumps(raw_response)),
                "has_full_data": True
            },
            "processed_summary": processed_summary,
            "chunk_summaries": chunk_summaries or [],
            "entity_strings": entity_strings,  # NEW: compact per-entity lines
            "created_at": datetime.now().isoformat(),
            "model_used": "cached_response"
        }
        
        try:
            # Save cache data
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Update index
            self.index[cache_key] = {
                "query_hash": cache_key,
                "endpoint": endpoint,
                "created_at": cache_data["created_at"],
                "last_accessed": cache_data["created_at"],
                "total_items": cache_data["raw_response_summary"]["total_items"],
                "summary_preview": processed_summary[:200] + "..." if len(processed_summary) > 200 else processed_summary
            }
            
            self._save_index()
            return cache_key
            
        except Exception as e:
            print(f"Warning: Could not cache response: {e}")
            return ""
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove a cache entry"""
        try:
            # Remove from index
            if cache_key in self.index:
                del self.index[cache_key]
                self._save_index()
            
            # Remove cache file
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            print(f"Warning: Could not remove cache entry: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.index)
        valid_entries = 0
        total_items_cached = 0
        
        for entry in self.index.values():
            if self._is_cache_valid(entry):
                valid_entries += 1
                total_items_cached += entry.get('total_items', 0)
        
        cache_size_mb = 0
        try:
            for file in self.cache_dir.glob("*.json"):
                cache_size_mb += file.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "total_items_cached": total_items_cached,
            "cache_size_mb": round(cache_size_mb, 2),
            "cache_directory": str(self.cache_dir)
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        expired_count = 0
        expired_keys = []
        
        for cache_key, entry in self.index.items():
            if not self._is_cache_valid(entry):
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            self._remove_cache_entry(cache_key)
            expired_count += 1
        
        return expired_count
    
    def search_cache(self, search_term: str) -> List[Dict[str, Any]]:
        """Search cached entries by summary content"""
        results = []
        search_term_lower = search_term.lower()
        
        for cache_key, entry in self.index.items():
            if not self._is_cache_valid(entry):
                continue
            
            # Search in summary preview
            if search_term_lower in entry.get('summary_preview', '').lower():
                results.append({
                    "cache_key": cache_key,
                    "endpoint": entry.get('endpoint'),
                    "created_at": entry.get('created_at'),
                    "total_items": entry.get('total_items'),
                    "summary_preview": entry.get('summary_preview')
                })
        
        # Sort by creation date (newest first)
        results.sort(key=lambda x: x['created_at'], reverse=True)
        return results
    
    def get_similar_queries(self, current_query: Dict[str, Any], endpoint: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar cached queries"""
        current_entity = current_query.get('query', {}).get('entity', '')
        current_fields = set(current_query.get('query', {}).get('fields', []))
        
        similar = []
        
        for cache_key, entry in self.index.items():
            if not self._is_cache_valid(entry) or entry.get('endpoint') != endpoint:
                continue
            
            # Load cached query for comparison
            try:
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    cached_query = cached_data.get('query', {})
                    cached_entity = cached_query.get('query', {}).get('entity', '')
                    cached_fields = set(cached_query.get('query', {}).get('fields', []))
                    
                    # Calculate similarity
                    if cached_entity == current_entity:
                        field_overlap = len(current_fields & cached_fields) / max(len(current_fields | cached_fields), 1)
                        
                        similar.append({
                            "cache_key": cache_key,
                            "similarity": field_overlap,
                            "summary_preview": entry.get('summary_preview'),
                            "created_at": entry.get('created_at'),
                            "total_items": entry.get('total_items')
                        })
            except Exception:
                continue
        
        # Sort by similarity and limit results
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:limit]
    
    def get_similar_cached_response(self, query: Dict[str, Any], endpoint: str, similarity_threshold: float = 0.8) -> Optional[Dict[str, Any]]:
        """Find and return similar cached response if similarity is above threshold"""
        similar_queries = self.get_similar_queries(query, endpoint, limit=1)
        
        if similar_queries and similar_queries[0]['similarity'] >= similarity_threshold:
            cache_key = similar_queries[0]['cache_key']
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    # Update last accessed time
                    if cache_key in self.index:
                        self.index[cache_key]['last_accessed'] = datetime.now().isoformat()
                        self._save_index()
                    
                    return cached_data
                except Exception as e:
                    print(f"Warning: Could not load similar cached data: {e}")
        
        return None
    
    def get_cached_response_by_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response by cache key"""
        if cache_key in self.index:
            cache_entry = self.index[cache_key]
            
            if self._is_cache_valid(cache_entry):
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r') as f:
                            return json.load(f)
                    except Exception as e:
                        print(f"Warning: Could not load cached data by key: {e}")
        
        return None

    def get_all_valid_entries(self, endpoint: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return loaded cached entries that are still valid.
        Optionally filter by endpoint and limit the number of results (newest first).
        """
        entries: List[Dict[str, Any]] = []
        keyed: List[tuple[str, Dict[str, Any]]] = []
        for cache_key, entry in self.index.items():
            if not self._is_cache_valid(entry):
                continue
            if endpoint and entry.get('endpoint') != endpoint:
                continue
            keyed.append((cache_key, entry))
        # Sort newest first by created_at
        def sort_key(item):
            _ = item[1].get('created_at')
            return _ if isinstance(_, str) else ""
        keyed.sort(key=lambda x: x[1].get('created_at', ''), reverse=True)
        if limit is not None:
            keyed = keyed[:max(0, int(limit))]
        for cache_key, _entry in keyed:
            try:
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                        entries.append(cached_data)
            except Exception:
                continue
        return entries

    def get_aggregate_entity_strings(self, endpoint: Optional[str] = None, limit_entries: Optional[int] = None, limit_lines: int = 10000) -> List[str]:
        """Aggregate per-entity strings across valid cache entries (optionally per endpoint)."""
        entries = self.get_all_valid_entries(endpoint=endpoint, limit=limit_entries)
        lines: List[str] = []
        for e in entries:
            try:
                if isinstance(e, dict) and isinstance(e.get('entity_strings'), list):
                    lines.extend(e['entity_strings'])
                    if len(lines) >= limit_lines:
                        return lines[:limit_lines]
            except Exception:
                continue
        return lines[:limit_lines]

    def _to_compact_string(self, item: Any) -> str:
        """Convert an item (likely a dict) to a compact, searchable string."""
        try:
            if isinstance(item, dict):
                fields = []
                # Prefer common keys if present
                for key in ["id", "name", "sender_name", "receiver_name", "description", "type", "status"]:
                    if key in item and item[key] is not None:
                        fields.append(f"{key}:{item[key]}")
                if fields:
                    return " | ".join(str(f) for f in fields)
                # Fallback to json dump
                return json.dumps(item, separators=(",", ":"))[:500]
            return str(item)[:500]
        except Exception:
            try:
                return json.dumps(item, default=str)[:500]
            except Exception:
                return str(item)
    
    def _extract_entity_strings(self, raw_response: Any) -> List[str]:
        """Extract a list of compact strings representing entities from API response."""
        entities: List[str] = []
        try:
            data = []
            if isinstance(raw_response, dict):
                if isinstance(raw_response.get('data'), list):
                    data = raw_response.get('data')
                else:
                    # maybe the dict itself is an entity list under another key
                    for v in raw_response.values():
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            data = v
                            break
            elif isinstance(raw_response, list):
                data = raw_response
            # Build strings
            for item in data[:10000]:  # cap to avoid uncontrolled growth
                entities.append(self._to_compact_string(item))
        except Exception:
            pass
        return entities

    def _to_compact_string(self, item: Any) -> str:
        """Convert an item (likely a dict) to a compact, searchable string with comprehensive field extraction."""
        try:
            if isinstance(item, dict):
                fields = []
                
                # Core identification fields
                core_keys = ["id", "external_id", "name", "description", "type", "status", "sequence"]
                for key in core_keys:
                    if key in item and item[key] is not None:
                        fields.append(f"{key}:{item[key]}")
                
                # Direct sender/receiver fields (if present at top level)
                sender_receiver_keys = ["sender_id", "sender_name", "receiver_id", "receiver_name"]
                for key in sender_receiver_keys:
                    if key in item and item[key] is not None:
                        fields.append(f"{key}:{item[key]}")
                
                # Extract from nested inventory object (common in WHINT data)
                if "inventory" in item and isinstance(item["inventory"], dict):
                    inventory = item["inventory"]
                    # Core inventory fields
                    for key in ["id", "name", "sender_name", "receiver_id", "receiver_name", "data_source_id"]:
                        if key in inventory and inventory[key] is not None:
                            fields.append(f"inv_{key}:{inventory[key]}")
                    
                    # Extract from nested data_source
                    if "data_source" in inventory and isinstance(inventory["data_source"], dict):
                        ds = inventory["data_source"]
                        if "id" in ds and ds["id"] is not None:
                            fields.append(f"data_source_id:{ds['id']}")
                        if "name" in ds and ds["name"] is not None:
                            fields.append(f"data_source_name:{ds['name']}")
                    
                    # Extract from nested receiver
                    if "receiver" in inventory and isinstance(inventory["receiver"], dict):
                        rec = inventory["receiver"]
                        if "id" in rec and rec["id"] is not None:
                            fields.append(f"receiver_id:{rec['id']}")
                        if "name" in rec and rec["name"] is not None:
                            fields.append(f"receiver_name:{rec['name']}")
                
                # Extract from nested sender object (if present)
                if "sender" in item and isinstance(item["sender"], dict):
                    sender = item["sender"]
                    for key in ["id", "name", "code", "system"]:
                        if key in sender and sender[key] is not None:
                            fields.append(f"sender_{key}:{sender[key]}")
                
                # Extract from nested receiver object (if present)  
                if "receiver" in item and isinstance(item["receiver"], dict):
                    receiver = item["receiver"]
                    for key in ["id", "name", "code", "system"]:
                        if key in receiver and receiver[key] is not None:
                            fields.append(f"receiver_{key}:{receiver[key]}")
                
                # Additional common metadata fields
                metadata_keys = [
                    "adapter", "protocol", "owner", "responsible", "complexity",
                    "last_traffic", "message_vpn", "data_flow_id", "inventory_id"
                ]
                for key in metadata_keys:
                    if key in item and item[key] is not None:
                        fields.append(f"{key}:{item[key]}")
                
                # E2E monitoring fields (if present)
                e2e_keys = ["E2E_T_URL", "E2E_S_URL", "E2E_T_HOST", "E2E_T_SRV"]
                for key in e2e_keys:
                    if key in item and item[key] is not None:
                        fields.append(f"{key}:{item[key]}")
                
                # If we found structured fields, return them
                if fields:
                    return " | ".join(str(f) for f in fields)
                
                # Fallback to JSON dump if no structured fields found
                return json.dumps(item, separators=(",", ":"))[:500]
            
            # Handle non-dict items
            return str(item)[:500]
            
        except Exception as e:
            # Ultimate fallback
            try:
                return json.dumps(item, default=str)[:500]
            except Exception:
                return str(item)[:500]

    def _endpoint_key(self, endpoint: str) -> str:
        """Create a filesystem-friendly key for endpoint grouping."""
        try:
            safe = endpoint.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace(":", "_")
            return safe
        except Exception:
            return "default"

    def _entity_store_path(self, endpoint: str) -> Path:
        """Path of the persistent entity store file for an endpoint."""
        key = self._endpoint_key(endpoint)
        return self.entity_store_dir / f"{key}.jsonl"

    def append_entity_strings_persistent(self, endpoint: str, entity_strings: List[str]) -> int:
        """Append unique entity strings to persistent store for the given endpoint.
        Returns number of new lines written.
        """
        try:
            path = self._entity_store_path(endpoint)
            existing: set[str] = set()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        existing.add(line.rstrip("\n"))
            # dedupe and cap per write batch
            new_lines = []
            for s in entity_strings:
                if s and s not in existing:
                    new_lines.append(s)
            if not new_lines:
                return 0
            with open(path, "a", encoding="utf-8") as f:
                for s in new_lines:
                    f.write(s.replace("\n", " ") + "\n")
            return len(new_lines)
        except Exception:
            return 0

    def load_entity_strings_persistent(self, endpoint: str, limit: Optional[int] = None) -> List[str]:
        """Load persistent entity strings for an endpoint (optionally limited)."""
        lines: List[str] = []
        try:
            path = self._entity_store_path(endpoint)
            if not path.exists():
                return []
            with open(path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if limit is not None and len(lines) >= limit:
                        break
                    lines.append(line.rstrip("\n"))
        except Exception:
            pass
        return lines