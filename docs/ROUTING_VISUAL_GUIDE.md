# Visual Routing Guide

## 🎯 The Problem (Before)

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  "Find SAP interfaces"                                       │
│                                                              │
│  Data Source: Local JSON File                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
                     ❌ CONFUSION ❌
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    GRAPH RAG                                 │
│                                                              │
│  1. Loads local JSON data                                   │
│  2. Adapts data for graph                                   │
│  3. Ingests into Neo4j (slow!)                              │
│  4. Queries Neo4j                                           │
│                                                              │
│  ⚠️ Problem: Using graph database for simple search!       │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ The Solution (After)

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  "Find SAP interfaces"                                       │
│                                                              │
│  Data Source: Local JSON File                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   ✅ SMART ROUTING ✅
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   METHOD ROUTER                              │
│                                                              │
│  Data Source: local_json → Use VECTOR RAG                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    VECTOR RAG                                │
│                                                              │
│  1. Load JSON data                                          │
│  2. Create embeddings                                       │
│  3. Semantic search                                         │
│  4. Return top-k results                                    │
│                                                              │
│  ✅ Fast, simple, appropriate for the task!                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Complete Routing Map

```
                        ┌─────────────┐
                        │ USER QUERY  │
                        └─────────────┘
                              ↓
                    ┌─────────────────┐
                    │ Select Source   │
                    └─────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Local JSON   │   │    DuckDB     │   │     API       │
│     File      │   │               │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        ↓                     ↓                     ↓
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  data_source  │   │  data_source  │   │  data_source  │
│ = local_json  │   │  = duckdb     │   │  = api        │
└───────────────┘   └───────────────┘   └───────────────┘
        ↓                     ↓                     ↓
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Method Router │   │ Method Router │   │ Method Router │
└───────────────┘   └───────────────┘   └───────────────┘
        ↓                     ↓                     ↓
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  VECTOR RAG   │   │   DB LOOKUP   │   │ Intent-Based  │
│               │   │               │   │   Routing     │
│ 📄 Semantic   │   │ 🗄️ SQL       │   │ 🌐 Priority  │
│    Search     │   │    Queries    │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## 🔄 Detailed Flow: Local JSON

```
1. USER SELECTS
   ┌─────────────────────────────────┐
   │ Data Source: Local JSON File    │
   │ File: 23-09-2025.json           │
   └─────────────────────────────────┘

2. MAPPING
   source = "Local JSON File"
   ↓
   data_source_type = "local_json"

3. ROUTING
   router.route_query(
       question, 
       data_source="local_json"
   )
   ↓
   method_name = "vector_rag"

4. EXECUTION
   ┌─────────────────────────────────┐
   │ Load JSON file                  │
   │ Extract data array              │
   │ Create embeddings               │
   │ Search semantically             │
   │ Return top-k results            │
   └─────────────────────────────────┘

5. RESULT
   📄 Relevant interfaces found
   ✅ Using simple vector search
```

---

## 🔄 Detailed Flow: DuckDB

```
1. USER SELECTS
   ┌─────────────────────────────────┐
   │ Data Source: DuckDB             │
   │ File: wic.duckdb                │
   └─────────────────────────────────┘

2. MAPPING
   source = "Local Engine (DuckDB)"
   ↓
   data_source_type = "duckdb"

3. ROUTING
   router.route_query(
       question,
       data_source="duckdb"
   )
   ↓
   method_name = "db_lookup"

4. EXECUTION
   ┌─────────────────────────────────┐
   │ Translate to SQL                │
   │ Execute query on DuckDB         │
   │ Return structured results       │
   │ No caching (always fresh)       │
   └─────────────────────────────────┘

5. RESULT
   🗄️ Direct SQL results
   ✅ Fast structured queries
```

---

## 🔄 Detailed Flow: Neo4j Graph

```
1. USER WANTS RELATIONSHIPS
   ┌─────────────────────────────────┐
   │ Question: "Path from A to B?"   │
   │ Requires: Graph relationships   │
   └─────────────────────────────────┘

2. ROUTING
   router.route_query(
       question,
       data_source="api"  # or "neo4j"
   )
   ↓
   Intent analysis: requires_graph=True
   ↓
   method_name = "graph_rag"

3. EXECUTION
   ┌─────────────────────────────────┐
   │ Query existing Neo4j data       │
   │ Find k-hop neighborhood         │
   │ Find shortest paths             │
   │ Return relationship insights    │
   │                                 │
   │ ⚠️ NO data ingestion           │
   └─────────────────────────────────┘

4. RESULT
   🕸️ Relationship analysis
   ✅ Graph-based insights
```

---

## 📊 Method Selection Logic

```python
def _select_method(intent, data_source):
    """
    ┌──────────────────────────────────────┐
    │ Is data_source == "local_json"?      │
    └──────────────────────────────────────┘
                    ↓ YES
            return 'vector_rag'
    
    ┌──────────────────────────────────────┐
    │ Is data_source == "duckdb"?          │
    └──────────────────────────────────────┘
                    ↓ YES
            return 'db_lookup'
    
    ┌──────────────────────────────────────┐
    │ Is data_source == "neo4j"?           │
    └──────────────────────────────────────┘
                    ↓ YES
            return 'graph_rag'
    
    ┌──────────────────────────────────────┐
    │ Is data_source == "api"?             │
    └──────────────────────────────────────┘
                    ↓ YES
    ┌──────────────────────────────────────┐
    │ Does intent require graph?           │
    └──────────────────────────────────────┘
                    ↓ YES
            return 'graph_rag'
                    ↓ NO
            Follow priority order
    """
```

---

## 🎨 Color-Coded Architecture

```
┌────────────────────────────────────────────────────────────┐
│                       🎯 USER QUERY                        │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                    🧭 METHOD ROUTER                        │
│              (Data Source + Intent Analysis)               │
└────────────────────────────────────────────────────────────┘
            ↓                   ↓                   ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 📄 VECTOR RAG    │  │ 🗄️ DB LOOKUP     │  │ 🕸️ GRAPH RAG     │
│                  │  │                  │  │                  │
│ 🔵 Local JSON    │  │ 🟢 DuckDB        │  │ 🔴 Neo4j         │
│ Semantic Search  │  │ SQL Queries      │  │ Relationships    │
│ Embeddings       │  │ Structured Data  │  │ Graph Patterns   │
│                  │  │                  │  │                  │
│ ✓ Fast           │  │ ✓ Very Fast      │  │ ✓ Specialized    │
│ ✓ Flexible       │  │ ✓ Structured     │  │ ✓ Connections    │
│ ✓ Simple         │  │ ✓ No Cache       │  │ ✓ Paths          │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 🔍 Real-World Examples

### Example 1: Finding SAP Interfaces

```
📝 Query: "Find all interfaces related to SAP"

🔵 LOCAL JSON (Vector RAG)
   ✅ Good choice
   - Load JSON → Embed → Search → Return
   - Fast semantic search
   
🟢 DUCKDB (DB Lookup)
   ✅ Good choice
   - SELECT * FROM interfaces WHERE name LIKE '%SAP%'
   - Very fast structured query
   
🔴 NEO4J (Graph RAG)
   ❌ Overkill
   - Only use if you need relationships
```

### Example 2: Counting Interfaces by Type

```
📝 Query: "How many interfaces are of each type?"

🔵 LOCAL JSON (Vector RAG)
   ⚠️ Not ideal
   - Can search but not great for aggregation
   
🟢 DUCKDB (DB Lookup)
   ✅ Perfect choice
   - SELECT type, COUNT(*) FROM interfaces GROUP BY type
   - Optimized for aggregation
   
🔴 NEO4J (Graph RAG)
   ❌ Wrong tool
   - Not about relationships
```

### Example 3: Data Flow Analysis

```
📝 Query: "How does data flow from SAP to Salesforce?"

🔵 LOCAL JSON (Vector RAG)
   ❌ Can't do relationships
   - Only semantic search
   
🟢 DUCKDB (DB Lookup)
   ❌ Can't do paths
   - No graph capabilities
   
🔴 NEO4J (Graph RAG)
   ✅ Perfect choice
   - MATCH path = (sap)-[*]-(salesforce)
   - Built for relationship analysis
```

---

## 🎯 Quick Decision Guide

```
┌─────────────────────────────────────────────────────────┐
│ NEED: Semantic search, exploration                      │
│ DATA: Local JSON file                                   │
│ USE:  📄 Vector RAG                                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ NEED: Filtering, aggregation, structured queries        │
│ DATA: DuckDB database                                   │
│ USE:  🗄️ DB Lookup                                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ NEED: Relationships, paths, connections                 │
│ DATA: Neo4j graph database                              │
│ USE:  🕸️ Graph RAG                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 Performance Comparison

```
TASK: Find 10 SAP interfaces from 10,000 records

📄 Vector RAG (Local JSON)
   Load: 2s | Embed: 5s | Search: 1s
   Total: ~8 seconds
   Memory: High (all embeddings)

🗄️ DB Lookup (DuckDB)
   Load: 0s | Query: 0.1s
   Total: ~0.1 seconds
   Memory: Low (database handles it)

🕸️ Graph RAG (Neo4j)
   Query: 0.5s
   Total: ~0.5 seconds
   Memory: Low (graph database)
   Note: Only if you need relationships!
```

---

## 🚦 Traffic Light Guide

### When to use each method:

```
📄 VECTOR RAG
🟢 JSON files with text content
🟢 Semantic similarity searches
🟢 Exploratory analysis
🟡 Structured data queries
🔴 Relationship analysis
🔴 Complex aggregations

🗄️ DB LOOKUP
🟢 Structured data in DuckDB
🟢 Filtering and aggregation
🟢 SQL-based operations
🟢 High-performance queries
🟡 Semantic searches
🔴 Relationship analysis

🕸️ GRAPH RAG
🟢 Relationship analysis
🟢 Path finding
🟢 Network analysis
🟢 Connected data
🔴 Simple searches
🔴 Aggregations
🔴 Unrelated data
```

Legend: 🟢 Excellent | 🟡 Possible | 🔴 Not Recommended

---

## 🎬 Summary Animation

```
Before Refactor:
┌─────────┐
│  Query  │ → Everything → GraphRAG → ❌ Slow, confused
└─────────┘

After Refactor:
┌─────────┐
│  Query  │ → Smart Router → {
└─────────┘                    📄 Vector RAG (JSON)
                               🗄️ DB Lookup (DuckDB)
                               🕸️ Graph RAG (Neo4j)
                             } → ✅ Fast, clear, appropriate
```

---

## ✨ The Key Takeaway

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  RIGHT TOOL FOR THE RIGHT JOB                           │
│                                                          │
│  📄 JSON     → Vector RAG   (Semantic Search)           │
│  🗄️ DuckDB   → DB Lookup    (SQL Queries)              │
│  🕸️ Neo4j    → Graph RAG    (Relationships)            │
│                                                          │
│  = Clear, Fast, Maintainable                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```


