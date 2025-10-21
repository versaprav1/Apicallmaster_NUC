"""
Zep/Episodic Memory Method

This method provides conversational memory and context recall using:
1. Local JSON storage (always available as fallback)
2. Optional Zep Cloud API integration (if configured)

Features:
- Session-based memory management
- Recent conversation recall
- Semantic search over conversation history
- Fact extraction and storage
- Automatic memory summarization
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class MemoryEntry:
    """A single memory entry"""
    session_id: str
    timestamp: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    facts: Optional[List[str]] = None


class LocalMemoryStore:
    """Local JSON-based memory storage"""
    
    def __init__(self, memory_dir: str = "memory_store"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.memory_dir / "sessions").mkdir(exist_ok=True)
        (self.memory_dir / "facts").mkdir(exist_ok=True)
    
    def add_memory(self, session_id: str, role: str, content: str, 
                   metadata: Optional[Dict[str, Any]] = None,
                   facts: Optional[List[str]] = None) -> str:
        """Add a memory entry"""
        timestamp = datetime.now().isoformat()
        
        entry = MemoryEntry(
            session_id=session_id,
            timestamp=timestamp,
            role=role,
            content=content,
            metadata=metadata,
            facts=facts
        )
        
        # Append to session file
        session_file = self.memory_dir / "sessions" / f"{session_id}.jsonl"
        with open(session_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
        
        return timestamp
    
    def get_recent_memories(self, session_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Get recent memories for a session"""
        session_file = self.memory_dir / "sessions" / f"{session_id}.jsonl"
        
        if not session_file.exists():
            return []
        
        memories = []
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entry_dict = json.loads(line)
                    memories.append(MemoryEntry(**entry_dict))
        
        # Return most recent
        return memories[-limit:]
    
    def search_memories(self, session_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Search memories by content (simple text match)"""
        session_file = self.memory_dir / "sessions" / f"{session_id}.jsonl"
        
        if not session_file.exists():
            return []
        
        query_lower = query.lower()
        matching_memories = []
        
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entry_dict = json.loads(line)
                    entry = MemoryEntry(**entry_dict)
                    
                    if query_lower in entry.content.lower():
                        matching_memories.append(entry)
        
        return matching_memories[-limit:]
    
    def get_all_facts(self, session_id: str) -> List[str]:
        """Get all extracted facts for a session"""
        facts_file = self.memory_dir / "facts" / f"{session_id}.json"
        
        if not facts_file.exists():
            return []
        
        with open(facts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def add_fact(self, session_id: str, fact: str):
        """Add a fact to the session's fact store"""
        facts_file = self.memory_dir / "facts" / f"{session_id}.json"
        
        # Load existing facts
        facts = []
        if facts_file.exists():
            with open(facts_file, 'r', encoding='utf-8') as f:
                facts = json.load(f)
        
        # Add new fact if not duplicate
        if fact not in facts:
            facts.append(fact)
            
            # Save updated facts
            with open(facts_file, 'w', encoding='utf-8') as f:
                json.dump(facts, f, indent=2)


def run(query: str, data: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "default",
        mode: str = "recent",
        top_k: int = 5,
        use_zep_api: bool = False,
        zep_api_key: Optional[str] = None,
        **kwargs) -> tuple[str, Dict[str, Any]]:
    """
    Zep/Episodic Memory: Recall conversation history and context.
    
    This method provides conversational memory using either:
    1. Local JSON storage (default, always available)
    2. Zep Cloud API (optional, if configured)
    
    Args:
        query: The user query
        data: Optional data context
        session_id: Session identifier for memory isolation
        mode: Memory recall mode ('recent', 'search', 'facts')
        top_k: Number of memories to recall
        use_zep_api: Whether to use Zep Cloud API
        zep_api_key: Zep API key (if using Zep API)
        **kwargs: Additional parameters
    
    Returns:
        summary: Recalled memories formatted as text
        meta: Metadata about the recall process
    """
    try:
        # Try Zep API first if enabled
        if use_zep_api and zep_api_key:
            try:
                return _zep_api_recall(query, session_id, mode, top_k, zep_api_key)
            except Exception as e:
                # Fall back to local storage
                print(f"Zep API failed, falling back to local storage: {e}")
        
        # Use local storage
        return _local_memory_recall(query, session_id, mode, top_k, data)
        
    except Exception as e:
        error_summary = f"❌ Memory recall failed: {str(e)}"
        meta = {
            "method": "zep_memory",
            "mode": mode,
            "error": str(e),
            "recalled": 0
        }
        return error_summary, meta


def _local_memory_recall(query: str, session_id: str, mode: str, 
                        top_k: int, data: Optional[List[Dict[str, Any]]]) -> tuple[str, Dict[str, Any]]:
    """Recall memories using local JSON storage"""
    memory_store = LocalMemoryStore()
    
    if mode == "recent":
        # Get recent conversation history
        memories = memory_store.get_recent_memories(session_id, limit=top_k)
        
        if memories:
            summary_parts = [f"📝 Recent Conversation History (Last {len(memories)} messages):\n"]
            
            for i, mem in enumerate(memories, 1):
                role_icon = "👤" if mem.role == "user" else "🤖"
                summary_parts.append(
                    f"\n{role_icon} **{mem.role.title()}** ({mem.timestamp}):\n"
                    f"{mem.content[:300]}{'...' if len(mem.content) > 300 else ''}\n"
                )
            
            summary = "\n".join(summary_parts)
            
            meta = {
                "method": "zep_memory",
                "mode": "recent",
                "storage": "local_json",
                "session_id": session_id,
                "recalled": len(memories)
            }
            
            return summary, meta
        else:
            summary = f"📝 No conversation history found for session '{session_id}'"
            meta = {
                "method": "zep_memory",
                "mode": "recent",
                "storage": "local_json",
                "session_id": session_id,
                "recalled": 0
            }
            return summary, meta
    
    elif mode == "search":
        # Search memories by content
        memories = memory_store.search_memories(session_id, query, limit=top_k)
        
        if memories:
            summary_parts = [f"🔍 Relevant Conversation History (Found {len(memories)} matches):\n"]
            
            for i, mem in enumerate(memories, 1):
                role_icon = "👤" if mem.role == "user" else "🤖"
                summary_parts.append(
                    f"\n**Match {i}** {role_icon} {mem.role.title()} ({mem.timestamp}):\n"
                    f"{mem.content[:300]}{'...' if len(mem.content) > 300 else ''}\n"
                )
            
            summary = "\n".join(summary_parts)
            
            meta = {
                "method": "zep_memory",
                "mode": "search",
                "storage": "local_json",
                "session_id": session_id,
                "query": query,
                "recalled": len(memories)
            }
            
            return summary, meta
        else:
            summary = f"🔍 No matching conversation history found for query: '{query}'"
            meta = {
                "method": "zep_memory",
                "mode": "search",
                "storage": "local_json",
                "session_id": session_id,
                "recalled": 0
            }
            return summary, meta
    
    elif mode == "facts":
        # Get extracted facts
        facts = memory_store.get_all_facts(session_id)
        
        if facts:
            summary_parts = [f"💡 Extracted Facts ({len(facts)} total):\n"]
            
            for i, fact in enumerate(facts[-top_k:], 1):
                summary_parts.append(f"{i}. {fact}")
            
            summary = "\n".join(summary_parts)
            
            meta = {
                "method": "zep_memory",
                "mode": "facts",
                "storage": "local_json",
                "session_id": session_id,
                "total_facts": len(facts),
                "recalled": min(len(facts), top_k)
            }
            
            return summary, meta
        else:
            summary = f"💡 No facts extracted yet for session '{session_id}'"
            meta = {
                "method": "zep_memory",
                "mode": "facts",
                "storage": "local_json",
                "session_id": session_id,
                "recalled": 0
            }
            return summary, meta
    
    else:
        summary = f"❌ Unknown mode: {mode}. Available modes: 'recent', 'search', 'facts'"
        meta = {
            "method": "zep_memory",
            "mode": mode,
            "error": f"Unknown mode: {mode}",
            "recalled": 0
        }
        return summary, meta


def _zep_api_recall(query: str, session_id: str, mode: str, 
                   top_k: int, api_key: str) -> tuple[str, Dict[str, Any]]:
    """Recall memories using Zep Cloud API"""
    try:
        # Import zep-python if available
        from zep_python import ZepClient
        from zep_python.memory import Memory, Message
        
        # Initialize Zep client
        client = ZepClient(api_key=api_key)
        
        if mode == "recent":
            # Get recent messages
            memory = client.memory.get(session_id=session_id)
            messages = memory.messages[-top_k:] if memory and memory.messages else []
            
            if messages:
                summary_parts = [f"📝 Recent Conversation (Zep API - Last {len(messages)} messages):\n"]
                
                for i, msg in enumerate(messages, 1):
                    role_icon = "👤" if msg.role == "user" else "🤖"
                    summary_parts.append(
                        f"\n{role_icon} **{msg.role.title()}**:\n"
                        f"{msg.content[:300]}{'...' if len(msg.content) > 300 else ''}\n"
                    )
                
                summary = "\n".join(summary_parts)
                
                meta = {
                    "method": "zep_memory",
                    "mode": "recent",
                    "storage": "zep_api",
                    "session_id": session_id,
                    "recalled": len(messages)
                }
                
                return summary, meta
            else:
                summary = f"📝 No conversation history in Zep for session '{session_id}'"
                meta = {
                    "method": "zep_memory",
                    "mode": "recent",
                    "storage": "zep_api",
                    "session_id": session_id,
                    "recalled": 0
                }
                return summary, meta
        
        elif mode == "search":
            # Search memories
            results = client.memory.search_sessions(
                text=query,
                limit=top_k
            )
            
            if results:
                summary_parts = [f"🔍 Search Results (Zep API - {len(results)} matches):\n"]
                
                for i, result in enumerate(results, 1):
                    summary_parts.append(
                        f"\n**Match {i}** (Score: {result.score:.2f}):\n"
                        f"{result.message[:300]}{'...' if len(result.message) > 300 else ''}\n"
                    )
                
                summary = "\n".join(summary_parts)
                
                meta = {
                    "method": "zep_memory",
                    "mode": "search",
                    "storage": "zep_api",
                    "query": query,
                    "recalled": len(results)
                }
                
                return summary, meta
            else:
                summary = f"🔍 No search results in Zep for query: '{query}'"
                meta = {
                    "method": "zep_memory",
                    "mode": "search",
                    "storage": "zep_api",
                    "recalled": 0
                }
                return summary, meta
        
        else:
            summary = f"❌ Mode '{mode}' not supported with Zep API"
            meta = {
                "method": "zep_memory",
                "mode": mode,
                "storage": "zep_api",
                "error": f"Mode not supported: {mode}",
                "recalled": 0
            }
            return summary, meta
            
    except ImportError:
        # Zep Python SDK not installed
        summary = "❌ Zep Python SDK not installed. Install with: pip install zep-python"
        meta = {
            "method": "zep_memory",
            "mode": mode,
            "storage": "zep_api",
            "error": "zep-python not installed",
            "recalled": 0
        }
        return summary, meta
    
    except Exception as e:
        # Zep API error
        summary = f"❌ Zep API error: {str(e)}"
        meta = {
            "method": "zep_memory",
            "mode": mode,
            "storage": "zep_api",
            "error": str(e),
            "recalled": 0
        }
        return summary, meta


# Helper function to add memories (can be called from app)
def add_memory(session_id: str, role: str, content: str, 
               metadata: Optional[Dict[str, Any]] = None,
               use_zep_api: bool = False,
               zep_api_key: Optional[str] = None):
    """
    Add a memory entry to storage.
    
    Args:
        session_id: Session identifier
        role: 'user' or 'assistant'
        content: Message content
        metadata: Optional metadata
        use_zep_api: Whether to use Zep API
        zep_api_key: Zep API key
    """
    if use_zep_api and zep_api_key:
        try:
            from zep_python import ZepClient
            from zep_python.memory import Memory, Message
            
            client = ZepClient(api_key=zep_api_key)
            client.memory.add(
                session_id=session_id,
                messages=[Message(role=role, content=content)]
            )
        except Exception as e:
            print(f"Failed to add to Zep API, using local storage: {e}")
            _add_to_local_storage(session_id, role, content, metadata)
    else:
        _add_to_local_storage(session_id, role, content, metadata)


def _add_to_local_storage(session_id: str, role: str, content: str, 
                          metadata: Optional[Dict[str, Any]] = None):
    """Add memory to local JSON storage"""
    memory_store = LocalMemoryStore()
    memory_store.add_memory(session_id, role, content, metadata) 