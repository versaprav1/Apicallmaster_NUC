# Data Source Routing Guide

## Overview

This guide explains how ApiCallMaster routes queries to different processing methods based on the data source. The system now has clear separation between different data access patterns.

## Data Source Types & Routing

### 🔍 **Local JSON File** → Simple Vector RAG

**Method Used:** `vector_rag`

**Purpose:** Semantic search over local JSON data using vector embeddings

**How it works:**
1. Loads data from local JSON file (e.g., `23-09-2025.json`)
2. Creates embeddings for data items
3. Performs semantic similarity search based on user query
4. Returns top-k most relevant results

**Use cases:**
- Searching through large JSON datasets
- Finding similar items based on meaning
- Quick exploratory analysis of local data

**Example queries:**
- "Find interfaces related to SAP"
- "Show me all interfaces with Azure in the name"
- "What interfaces send data to Salesforce?"

**Configuration:**
```python
source = "Local JSON File"
local_file = "path/to/data.json"
```

---

### 🗄️ **DuckDB** → Direct SQL Queries

**Method Used:** `db_lookup`

**Purpose:** Direct SQL execution against DuckDB database

**How it works:**
1. Translates user query to DuckDB SQL
2. Executes SQL query directly on database
3. Returns structured results
4.  execution (no caching)

**Use cases:**
- Complex filtering and aggregation
- High-performance queries on large datasets
- Structured data analysis
- SQL-based operations (JOIN, GROUP BY, etc.)

**Example queries:**
- "How many interfaces are of type SAP?"
- "List all interfaces grouped by type"
- "Count interfaces by sender system"

**Configuration:**
```python
source = "Local Engine (DuckDB)"
duckdb_path = "duckdb_engine/wic.duckdb"
```

**Key Features:**
- ✅  execution
- ✅ No caching
- ✅ Direct SQL translation
- ✅ High performance for structured queries

---

### 🕸️ **Neo4j Graph** → Graph RAG

**Method Used:** `graph_rag`

**Purpose:** Relationship analysis using graph database

**How it works:**
1. Queries Neo4j graph database
2. Extracts entities from user query
3. Finds k-hop neighborhoods around entities
4. Discovers shortest paths between systems
5. Returns relationship-based insights

**Use cases:**
- Finding connections between systems
- Analyzing data flows
- Understanding integration patterns
- Path discovery between sender/receiver

**Example queries:**
- "What is the path from System A to System B?"
- "Show all systems connected to Salesforce"
- "How does data flow from SAP to Azure?"
- "What systems are 2 hops away from SAP?"

**UI Configuration:**
```python
# In Streamlit app, select:
source = "Neo4j Graph"

# Then configure:
neo4j_uri = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_password = "your_password"
```

**Environment Variables (alternative):**
```python
# Neo4j connection (environment variables)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GRAPH_BACKEND=neo4j
```

**Important Notes:**
- ⚠️ Data must be **pre-loaded** into Neo4j
- ⚠️ Graph RAG does **NOT** ingest data on-the-fly
- ⚠️ Use separate ingestion scripts to populate Neo4j
- ✅ Now has dedicated UI option in Streamlit app

---

### 🌐 **API** → Intent-Based Routing

**Method Used:** Intent-based selection (priority: `graph_rag` → `vector_rag` → `db_lookup`)

**Purpose:** Live data fetching from WHINT API

**How it works:**
1. Analyzes query intent
2. If relationships are needed → uses `graph_rag`
3. Otherwise, follows priority order
4. Executes against live API
5. No caching ()

**Use cases:**
- Real-time data access
- Production data queries
- Up-to-date information

**Configuration:**
```python
source = "API"
# Credentials required:
api_url = "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
api_key = "your_api_key"
username = "your_username"
password = "your_password"
```

---

## Routing Decision Tree

```
User Query
    ↓
┌───────────────────────────────┐
│ Determine Data Source         │
└───────────────────────────────┘
    ↓
    ├─ Local JSON File ──→ vector_rag (Simple Vector RAG)
    │
    ├─ DuckDB ──→ db_lookup (Direct SQL Queries)
    │
    ├─ Neo4j Graph ──→ graph_rag (Graph Relationships)
    │
    └─ API ──→ Intent-based routing
                    ↓
                ┌─────────────────────────┐
                │ Analyze Query Intent    │
                └─────────────────────────┘
                    ↓
                    ├─ Requires relationships? → graph_rag
                    ├─ Semantic search? → vector_rag
                    ├─ Structured query? → db_lookup
                    └─ Default → Follow priority order
```

---

## Method Comparison

| Feature | Vector RAG | DB Lookup | Graph RAG |
|---------|------------|-----------|-----------|
| **Data Source** | Local JSON | DuckDB | Neo4j |
| **Query Type** | Semantic | SQL | Graph |
| **Performance** | Medium | Fast | Medium |
| **Caching** | Yes | No | No |
| **Best For** | Exploratory | Structured | Relationships |
| **Data Prep** | Load JSON | Import to DuckDB | Pre-load Neo4j |

---

## Code Examples

### Using Vector RAG (Local JSON)

```python
from src.method_router import MethodRouter

router = MethodRouter(openai_api_key="sk-...")

# Route query for local JSON
result = router.route_query(
    user_question="Find SAP interfaces",
    data_source="local_json"
)

# Will return: method_name = "vector_rag"
```

### Using DB Lookup (DuckDB)

```python
from src.method_router import MethodRouter

router = MethodRouter(openai_api_key="sk-...")

# Route query for DuckDB
result = router.route_query(
    user_question="Count interfaces by type",
    data_source="duckdb"
)

# Will return: method_name = "db_lookup"
```

### Using Graph RAG (Neo4j)

```python
from src.method_router import MethodRouter

router = MethodRouter(openai_api_key="sk-...")

# Route query for Neo4j
result = router.route_query(
    user_question="Show path from SAP to Salesforce",
    data_source="neo4j"
)

# Will return: method_name = "graph_rag"
```

---

## Configuration

### Environment Variables

```bash
# Method Configuration
METHODS_ENABLED=graph_rag,vector_rag,db_lookup,llm_synthesis
METHOD_PRIORITY=graph_rag,vector_rag,db_lookup

# Graph RAG Configuration
GRAPH_BACKEND=neo4j
GRAPH_MAX_HOPS=2
GRAPH_PATH_LIMIT=5

# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM Configuration
OPENAI_API_KEY=sk-...
```

---

## Best Practices

### ✅ DO:
- Use **Vector RAG** for exploratory semantic search on local JSON files
- Use **DB Lookup** for fast, structured queries on DuckDB
- Use **Graph RAG** for relationship and path analysis in Neo4j
- Pre-load data into Neo4j before using Graph RAG
- Keep data sources separate and focused

### ❌ DON'T:
- Don't expect Graph RAG to ingest data on-the-fly
- Don't mix data sources in a single query
- Don't use Vector RAG for structured SQL queries
- Don't use DB Lookup for relationship analysis

---

## Troubleshooting

### Issue: Graph RAG returns empty results

**Solution:**
1. Check if Neo4j is running
2. Verify data is loaded in Neo4j: `MATCH (n) RETURN count(n)`
3. Check connection settings in environment variables

### Issue: Vector RAG is slow

**Solution:**
1. Reduce JSON file size
2. Increase `top_k` limit
3. Use DuckDB for better performance on large datasets

### Issue: DuckDB query fails

**Solution:**
1. Check if DuckDB file exists
2. Verify data is imported correctly
3. Check SQL translation in diagnostics

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Method Router                              │
│  (Analyzes data source + intent)                            │
└─────────────────────────────────────────────────────────────┘
         ↓                  ↓                  ↓
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Vector RAG    │  │   DB Lookup    │  │   Graph RAG    │
│                │  │                │  │                │
│  Local JSON    │  │    DuckDB      │  │    Neo4j       │
│  Semantic      │  │    Direct SQL  │  │    Graph       │
│  Search        │  │    Queries     │  │    Relations   │
└────────────────┘  └────────────────┘  └────────────────┘
         ↓                  ↓                  ↓
┌─────────────────────────────────────────────────────────────┐
│                      LLM Synthesis                           │
│            (Format & present results)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary

The refactored routing system provides:
1. **Clear separation** between data sources
2. **Optimized methods** for each data type
3. **No confusion** about which method handles what
4. **Better performance** by using the right tool for the job

### Quick Reference

- 📄 **Local JSON** = Vector RAG (semantic search)
- 🗄️ **DuckDB** = DB Lookup (SQL queries)
- 🕸️ **Neo4j** = Graph RAG (relationships only)
- 🌐 **API** = Intent-based routing

---

## See Also

- [Method Router Implementation](../src/method_router.py)
- [Vector RAG Documentation](../methods/vector_rag.py)
- [DB Lookup Documentation](../methods/db_lookup.py)
- [Graph RAG Documentation](../methods/graph_rag.py)


