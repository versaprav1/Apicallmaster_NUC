# Data Source Routing Refactor - Summary

## 🎯 Objective

Separate the different ways the LLM can interact with data:
- **Local JSON** → Simple Vector RAG (semantic search)
- **DuckDB** → Direct SQL queries (no RAG)
- **GraphRAG** → Only for Neo4j graph relationships

## ✅ Changes Made

### 1. **Updated `src/method_router.py`**

#### Added Data Source Awareness
- Modified `route_query()` to accept `data_source` parameter
- Updated `_select_method()` to route based on data source type

#### New Routing Logic
```python
Data Source Routing:
  - local_json: Always use vector_rag (simple vector search)
  - duckdb: Always use db_lookup (direct SQL queries)
  - neo4j: Always use graph_rag (graph relationships)
  - api: Use intent-based routing with priority
```

**Key Changes:**
- Added `data_source: str = "api"` parameter to `route_query()`
- Implemented explicit data source routing in `_select_method()`
- GraphRAG now only used when `data_source == "neo4j"` or when intent requires it

---

### 2. **Updated `app.py`**

#### Mapping Data Sources
```python
if source == "Local JSON File":
    data_source_type = "local_json"
elif source == "Local Engine (DuckDB)":
    data_source_type = "duckdb"
else:  # API
    data_source_type = "api"
```

#### New Processing Flow

**GraphRAG (Neo4j Only):**
- Removed data ingestion logic
- No longer processes local JSON or DuckDB data
- Only queries existing Neo4j database
- Shows clear error if Neo4j is not available

**Vector RAG (Local JSON):**
- New handler for Local JSON files
- Loads JSON data
- Performs semantic vector search
- Returns top-k relevant results

**DB Lookup (DuckDB):**
- Continues to DuckDB processing section
- Direct SQL query execution
- No GraphRAG interference

**Key Changes:**
- Pass `data_source_type` to `router.route_query()`
- Split handling into three distinct sections
- Removed GraphRAG from local data processing
- Added clear status messages for each method

---

### 3. **Updated `methods/graph_rag.py`**

#### Removed Data Ingestion
- GraphRAG no longer ingests data on-the-fly
- Removed `adapt_data_for_graph_rag()` calls
- Removed `bulk_upsert()` logic
- Added deprecation warning if `data` parameter is provided

#### New Behavior
```python
# Old: Ingest data then query
if data:
    adapt_data_for_graph_rag(data)
    store.bulk_upsert(adapted_data)

# New: Only query existing Neo4j data
if data:
    # Warning: data parameter is deprecated
    # GraphRAG only queries existing Neo4j data
```

**Key Changes:**
- Updated docstring to clarify Neo4j-only usage
- Removed all data ingestion code
- Added warnings if data is provided
- Focuses on querying existing graph relationships

---

### 4. **Created Documentation**

#### New File: `docs/DATA_SOURCE_ROUTING_GUIDE.md`

Comprehensive guide covering:
- Overview of routing system
- Detailed explanation of each data source
- Routing decision tree
- Method comparison table
- Code examples
- Configuration guide
- Best practices
- Troubleshooting
- Architecture diagram

---

## 📊 Before vs After

### Before (Mixed Routing)

```
Local JSON ──┐
             ├──→ GraphRAG (with ingestion)
DuckDB ──────┘

Neo4j ──────────→ GraphRAG (query)

API ────────────→ Intent-based routing
```

**Problems:**
- GraphRAG used for all data sources
- Confusion about which method handles what
- Data ingestion happening during queries
- No clear separation

### After (Clear Separation)

```
Local JSON ──────→ Vector RAG (semantic search)

DuckDB ──────────→ DB Lookup (direct SQL)

Neo4j ───────────→ Graph RAG (relationships only)

API ─────────────→ Intent-based routing
```

**Benefits:**
- Clear separation of concerns
- Right tool for the right job
- No data ingestion during queries
- Predictable behavior

---

## 🎨 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         User Query                            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                      Method Router                            │
│           (Data Source Awareness + Intent Analysis)          │
└──────────────────────────────────────────────────────────────┘
          ↓                    ↓                    ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Vector RAG     │  │    DB Lookup     │  │   Graph RAG      │
│                  │  │                  │  │                  │
│  📄 Local JSON   │  │  🗄️ DuckDB       │  │  🕸️ Neo4j        │
│  Semantic Search │  │  Direct SQL      │  │  Relationships   │
│  Embeddings      │  │  Structured      │  │  Graph Queries   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 🔧 Usage Examples

### Local JSON with Vector RAG

```python
# In app.py, select data source
source = "Local JSON File"
local_file = "23-09-2025.json"

# Query will automatically use vector_rag
user_question = "Find interfaces related to SAP"

# Router determines method based on data source
routing_result = method_router.route_query(
    user_question, 
    data_source="local_json"
)

# Result: method_name = "vector_rag"
```

### DuckDB with DB Lookup

```python
# In app.py, select data source
source = "Local Engine (DuckDB)"
duckdb_path = "duckdb_engine/wic.duckdb"

# Query will automatically use db_lookup
user_question = "Count interfaces by type"

# Router determines method based on data source
routing_result = method_router.route_query(
    user_question,
    data_source="duckdb"
)

# Result: method_name = "db_lookup"
```

### Neo4j with Graph RAG

```python
# GraphRAG is only used when explicitly needed
# or when data source is neo4j

# Option 1: Explicit Neo4j data source
routing_result = method_router.route_query(
    "Show path from SAP to Salesforce",
    data_source="neo4j"
)

# Option 2: API with relationship intent
routing_result = method_router.route_query(
    "How is System A connected to System B?",
    data_source="api"
)
# Router will detect relationship requirement
# and use graph_rag
```

---

## 🚀 Benefits

1. **Clear Separation**
   - Each data source has a dedicated method
   - No confusion about which method to use
   - Predictable behavior

2. **Better Performance**
   - Right tool for the right job
   - No unnecessary data processing
   - Optimized for each data type

3. **Maintainability**
   - Code is clearer and easier to understand
   - Each method has a single responsibility
   - Easier to debug and extend

4. **No Data Mixing**
   - GraphRAG doesn't ingest local data
   - Vector RAG focuses on semantic search
   - DB Lookup focuses on SQL queries

---

## ⚠️ Breaking Changes

### GraphRAG Data Parameter

**Old Behavior:**
```python
# GraphRAG would ingest data on-the-fly
graph_rag.run(query="...", data=local_data)
```

**New Behavior:**
```python
# GraphRAG only queries Neo4j, data parameter is deprecated
graph_rag.run(query="...")  # Data must be pre-loaded in Neo4j
```

### Data Loading

- **Local JSON**: Handled by Vector RAG
- **DuckDB**: Must be pre-loaded using ingestion scripts
- **Neo4j**: Must be pre-loaded using separate ingestion tools

---

## 📝 Migration Guide

### If you were using GraphRAG with local data:

1. **Identify your data source:**
   - JSON files → Use Vector RAG
   - DuckDB → Use DB Lookup
   - Neo4j → Continue using Graph RAG

2. **Update data source selection:**
   ```python
   # Old
   source = "API"  # but using local data
   
   # New
   source = "Local JSON File"  # for JSON
   source = "Local Engine (DuckDB)"  # for DuckDB
   ```

3. **Pre-load data into Neo4j:**
   ```bash
   # Use ingestion scripts to load data into Neo4j
   python scripts/neo4j/ingest_data.py
   ```

---

## 🧪 Testing

### Test Vector RAG
1. Select "Local JSON File" as data source
2. Provide path to JSON file
3. Ask a semantic question
4. Verify method used is `vector_rag`

### Test DB Lookup
1. Select "Local Engine (DuckDB)" as data source
2. Provide path to DuckDB file
3. Ask a structured query
4. Verify method used is `db_lookup`

### Test Graph RAG
1. Ensure Neo4j is running and has data
2. Select "API" as data source (or use Neo4j directly)
3. Ask a relationship question
4. Verify method used is `graph_rag`

---

## 📚 Documentation

- **Main Guide**: `docs/DATA_SOURCE_ROUTING_GUIDE.md`
- **This Summary**: `ROUTING_REFACTOR_SUMMARY.md`
- **Code**: 
  - `src/method_router.py`
  - `app.py`
  - `methods/graph_rag.py`
  - `methods/vector_rag.py`
  - `methods/db_lookup.py`

---

## ✨ Summary

The refactoring successfully separates data source handling:

- ✅ **Local JSON** now uses simple Vector RAG (semantic search)
- ✅ **DuckDB** now uses direct SQL queries (db_lookup)
- ✅ **GraphRAG** is now exclusively for Neo4j graph relationships
- ✅ Clear routing logic with data source awareness
- ✅ Comprehensive documentation
- ✅ No linter errors
- ✅ Backward compatible (with deprecation warnings)

**Result:** A cleaner, more maintainable system with clear separation of concerns.


