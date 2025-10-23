# Complete Flow Analysis: User Question to Answer (All Data Sources)

## Overview
This document shows the complete flow from user question to answer for all 4 data sources supported by the WHINT API AI Assistant.

---

## 1. 🕸️ NEO4J GRAPH (GraphRAG)

### Flow Diagram
```
User Question: "Show all systems connected to Salesforce"
    ↓
1. DATA SOURCE SELECTION
   - User selects "Neo4j Graph" from radio buttons
   - data_source_type = "neo4j"
    ↓
2. QUERY ROUTING
   - MethodRouter.route_query() analyzes intent
   - Determines method_name = "graph_rag"
   - Sets method_params with graph-specific parameters
    ↓
3. SEED EXTRACTION (methods/graph_rag.py:16-58)
   - Extract system names from query using regex
   - Common systems: ['salesforce', 'sap', 'azure', 'aws', ...]
   - Result: seeds = ['Salesforce']
    ↓
4. NEO4J QUERY (methods/graph_rag.py:118-120)
   - Call: store.k_hop_neighborhood(seed_names=['Salesforce'], max_hops=2, limit=1000)
   - Cypher Query: Find all interfaces and systems within 2 hops of 'Salesforce'
   - Result: neighborhood = [13 interface records]
    ↓
5. RAW RESULTS FORMATTING (methods/graph_rag.py:149-231)
   - Convert Neo4j records to readable format
   - Group by type (Systems vs Interfaces)
   - Result: neighborhood_lines = [13 interface names]
    ↓
6. LLM SYNTHESIS PROMPT CREATION (methods/graph_rag.py:237-246)
   - Create synthesis_prompt with ALL available data
   - Include: query, seeds, neighborhood count, ALL interface names
    ↓
7. LLM GENERATION (methods/graph_rag.py:249-253)
   - System Prompt: "You are an expert in system integration and API analysis..."
   - User Prompt: synthesis_prompt (contains ALL data)
   - Model: llama3.2:latest (or selected model)
    ↓
8. RESPONSE COMBINATION (methods/graph_rag.py:256-264)
   - Combine raw results + LLM response with headings
   - Format: "## 🔍 Neo4j Query Results" + "## 🤖 [model] Response"
```

### Key Characteristics
- **No Data Loading**: Works directly with Neo4j database
- **Graph Queries**: Uses Cypher queries for relationship analysis
- **LLM Integration**: Uses selected model for natural language synthesis
- **Complete Context**: All results sent to LLM in single prompt

---

## 2. 📄 LOCAL JSON FILE (VectorRAG)

### Flow Diagram
```
User Question: "List all SAP interfaces"
    ↓
1. DATA SOURCE SELECTION
   - User selects "Local JSON File" from radio buttons
   - data_source_type = "local_json"
    ↓
2. QUERY ROUTING
   - MethodRouter.route_query() analyzes intent
   - Determines method_name = "vector_rag"
   - Sets method_params with vector-specific parameters
    ↓
3. DATA LOADING (app.py:1704-1715)
   - Load JSON file from specified path
   - Parse and validate JSON structure
   - Extract data array if nested in object
    ↓
4. VECTOR STORE INITIALIZATION (methods/vector_rag.py:40)
   - Initialize VectorKnowledgeStore (ChromaDB)
   - Load sentence transformer model
    ↓
5. SEMANTIC SEARCH (methods/vector_rag.py:43-48)
   - Strategy 1: Search stored Q&A pairs first
   - Call: vector_store.find_similar_qa(question, data_source="local_json", top_k=5)
   - Filter by similarity threshold (0.7)
    ↓
6. FALLBACK SEARCH (methods/vector_rag.py:60-80)
   - If no Q&A pairs found, search raw data
   - Create embeddings for query and data items
   - Calculate cosine similarity scores
   - Return top-k most similar items
    ↓
7. RESULT FORMATTING (methods/vector_rag.py:85-95)
   - Format retrieved chunks as readable text
   - Include similarity scores and metadata
   - Return summary string and metadata
```

### Key Characteristics
- **File Loading**: Loads JSON data from local file system
- **Semantic Search**: Uses vector embeddings for similarity matching
- **Q&A Caching**: Checks for similar questions first
- **Fallback Strategy**: Raw data search if no cached Q&A found

---

## 3. 🦆 LOCAL ENGINE (DuckDB) (API Call + Analysis)

### Flow Diagram
```
User Question: "Show me all active interfaces"
    ↓
1. DATA SOURCE SELECTION
   - User selects "Local Engine (DuckDB)" from radio buttons
   - data_source_type = "duckdb"
    ↓
2. QUERY ROUTING
   - MethodRouter.route_query() analyzes intent
   - Determines method_name = "api_call" (fallback)
   - Sets method_params with API-specific parameters
    ↓
3. API QUERY GENERATION (app.py:1750-1760)
   - Generate API query based on user question
   - Map natural language to API parameters
   - Create structured query object
    ↓
4. VECTOR STORE CHECK (app.py:1767-1775)
   - Check for similar questions in vector store
   - Call: vector_store.find_similar_qa(question, data_source="duckdb", top_k=3)
   - If similarity > 0.85, return cached answer
    ↓
5. DUCKDB EXECUTION (app.py:1780-1790)
   - Execute API query against DuckDB database
   - Translate API query to SQL
   - Run SQL query and get results
    ↓
6. LLM ANALYSIS (app.py:1795-1805)
   - Use selected LLM model to analyze results
   - Generate natural language explanation
   - Extract insights and patterns
    ↓
7. VECTOR STORE CACHING (app.py:1807-1820)
   - Store Q&A pair in vector database
   - Cache for future similar questions
   - Return analysis with metadata
```

### Key Characteristics
- **Fresh Execution**: Always executes queries (no stale cache)
- **SQL Translation**: Converts API queries to SQL
- **LLM Analysis**: Uses selected model to analyze results
- **Smart Caching**: Caches results for future similar questions

---

## 4. 🌐 API (API Call + Analysis)

### Flow Diagram
```
User Question: "Get all interfaces from production"
    ↓
1. DATA SOURCE SELECTION
   - User selects "API" from radio buttons
   - data_source_type = "api"
    ↓
2. QUERY ROUTING
   - MethodRouter.route_query() analyzes intent
   - Determines method_name = "api_call" (fallback)
   - Sets method_params with API-specific parameters
    ↓
3. API QUERY GENERATION (app.py:1750-1760)
   - Generate API query based on user question
   - Map natural language to API parameters
   - Create structured query object
    ↓
4. AUTHENTICATION CHECK (app.py:1765-1770)
   - Verify API credentials are available
   - Check authentication status
   - Validate API endpoint accessibility
    ↓
5. API EXECUTION (app.py:1775-1785)
   - Execute API query against external API
   - Send HTTP request with credentials
   - Handle response and error cases
    ↓
6. LLM ANALYSIS (app.py:1790-1800)
   - Use selected LLM model to analyze API response
   - Generate natural language explanation
   - Extract insights and patterns
    ↓
7. RESULT FORMATTING (app.py:1805-1815)
   - Format API response as readable text
   - Include metadata and execution details
   - Return analysis with context
```

### Key Characteristics
- **External API**: Calls external API endpoints
- **Authentication**: Requires valid API credentials
- **Real-time Data**: Gets fresh data from external source
- **LLM Analysis**: Uses selected model to analyze responses

---

## Common Flow Elements

### 1. Query Routing (src/method_router.py)
All data sources go through the same routing logic:
- **Intent Analysis**: NLPProcessor analyzes user intent
- **Method Selection**: Chooses appropriate method based on data source
- **Parameter Setup**: Configures method-specific parameters

### 2. LLM Integration
All methods can use the selected LLM model:
- **Model Selection**: User selects from available models (including Ollama)
- **API Key Check**: Verifies model accessibility
- **Response Generation**: Uses model for natural language processing

### 3. Response Logging
All responses are logged with:
- **Question**: Original user question
- **Answer**: Generated response
- **Method**: Processing method used
- **Data Source**: Source of data
- **Metadata**: Additional context and timing

### 4. Error Handling
Consistent error handling across all methods:
- **Graceful Fallbacks**: Fallback to alternative methods
- **User Feedback**: Clear error messages
- **Logging**: Error details logged for debugging

---

## Data Source Comparison

| Aspect | Neo4j Graph | Local JSON | DuckDB | API |
|--------|-------------|------------|--------|-----|
| **Data Source** | Graph Database | Local File | Local Database | External API |
| **Query Type** | Graph/Cypher | Vector/Semantic | SQL | HTTP |
| **Caching** | No | Yes (Q&A) | Yes (Q&A) | No |
| **LLM Integration** | Yes (Synthesis) | No | Yes (Analysis) | Yes (Analysis) |
| **Real-time** | Yes | No | Yes | Yes |
| **Offline** | Yes | Yes | Yes | No |
| **Use Case** | Relationships | Document Search | Data Analysis | External Integration |

---

## Method-Specific Details

### GraphRAG (Neo4j)
- **Seeds**: Extracted from user query
- **Neighborhood**: 2-hop graph traversal
- **Limit**: 1000 results (increased from 200)
- **LLM**: Full context synthesis

### VectorRAG (Local JSON)
- **Embeddings**: Sentence transformers
- **Similarity**: Cosine similarity
- **Threshold**: 0.7 minimum
- **Fallback**: Raw data search

### DuckDB (Local Engine)
- **Translation**: API → SQL
- **Execution**: Fresh every time
- **Caching**: Q&A pairs only
- **Analysis**: LLM post-processing

### API (External)
- **Authentication**: Credential-based
- **Execution**: HTTP requests
- **Analysis**: LLM post-processing
- **Real-time**: Live data access
