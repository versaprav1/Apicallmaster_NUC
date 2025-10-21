# WHINT API AI Assistant

An intelligent natural-language interface for WHINT API. Ask questions in plain English → get structured results. Translates NL → WHINT JSON queries, routes to the right endpoint, executes via Live API or Local engines, and formats answers using multi-provider LLMs with smart caching.

## What It Does

- Natural language → WHINT JSON query (validated, retried if needed)
- Cache-first answers with fuzzy reuse and 30-day TTL
- Intent-based responses (list/count/search/analysis)
- Execution modes: Live API, Local JSON, DuckDB
- Multi-provider LLMs: OpenAI, Gemini, Anthropic, Groq, OpenRouter, Ollama

## Quick Start

1. Ensure Python 3.11+
2. Install dependencies (uv or pip)

```bash
# Using uv
uv sync

# Or using pip
pip install -r requirements.txt  # if present
```

3. Add credentials to `.env` or Streamlit secrets (see Configuration)
4. Run the app

```bash
streamlit run app.py
```

## Key Features

- Intent-based responses (95.7% accuracy)
  - list_names, count, specific_search, analysis
- Smart caching
  - Exact hit → instant
  - Fuzzy match → reuse
  - Aggregate synthesis → combine cache
  - Miss → live call then cache (TTL 30d)
- Three execution modes
  - Live WHINT API
  - Local JSON executor
  - DuckDB engine
- Multi-provider LLMs with auto selection and failover

## Technology Stack

- Streamlit UI
- OpenAI / Google Gemini / Anthropic / Groq / OpenRouter / Ollama
- ChromaDB + sentence-transformers (semantic search)
- DuckDB (local SQL)
- requests, pandas, pyarrow, python-dotenv

## Architecture Overview

User Question → Intent Analysis → Query Translation (LLM)
  ↓
Endpoint Routing → Cache Check → [API | Local | DuckDB]
  ↓
Response Analysis (LLM) → Format by Intent → Display

Core modules:
- `app.py` – UI, routing, execution paths, answer formatting
- `src/prompt_builder.py` – system prompts for translation/synthesis
- `src/llm_providers.py` – provider selection and invocation
- `src/knowledge_store.py` – cache + fuzzy match + persistent entities
- `local_executor/` – offline JSON execution
- `duckdb_engine/` – local SQL execution

## Configuration

Environment variables (at least WHINT and one LLM key):

```env
WHINT_API_BASE_URL=...
WHINT_API_X_API_KEY=...
WHINT_USERNAME=...
WHINT_PASSWORD=...

OPENAI_API_KEY=...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
```

Credential priority:
1) Environment variables
2) Streamlit secrets
3) Local `.env`
4) Manual UI entry

See `docs/API_KEY_SETUP_GUIDE.md` for provider details and model guidance.

## Project Structure (abridged)

```
ApiCallMaster/
├── app.py
├── src/
│   ├── knowledge_store.py
│   ├── llm_providers.py
│   ├── prompt_builder.py
│   └── whint_api.py
├── local_executor/
├── duckdb_engine/
├── docs/
├── knowledge_cache/
└── knowledge_entities/
```

## Workflow

End-to-end answer flow (what happens when you ask a question)
1) App UI (Streamlit) in ApiCallMaster/app.py
chat_page() collects your question and selected LLM model.
Calls create_api_query(user_question, selected_model).
2) Turn your question into a JSON API query
create_api_query builds a system prompt via build_system_prompt_translation (in ApiCallMaster/src/prompt_builder.py).
Uses LLMProviderManager to call the selected LLM, which returns a JSON query (validated/parsed).
If the LLM doesn’t return valid JSON, it retries with stricter instructions; otherwise falls back to a safe default query.
3) Decide which WHINT API endpoint to call
determine_api_endpoint(query, base_url) inspects type filters in the query.
Routes to /interfaces/sap, /interfaces/mule, /interfaces/azure, /interfaces/apim, or default /interfaces.
4) Cache-first retrieval
KnowledgeStore is checked to find a cached response for the query+endpoint.
If a cache hit:
The app uses cached data for the answer (no API call).
The response type depends on intent:
Name list → generate_list_response(...)
Count → generate_count_response(...)
Search → generate_search_response(...)
Otherwise → use cached processed summary.
5) Aggregate cache fallback (if no exact hit)
If there are similar/aggregate cached entries for the same endpoint, the app synthesizes an answer from cached summaries without calling the API.
6) Live WHINT API call (if no cache path used)
execute_api_query(query, credentials) POSTs the JSON query to the determined endpoint.
Credentials come from session, env, or Streamlit secrets.
On 200 OK, the live API response is returned.
7) Turn raw data into a readable answer
analyze_response(user_question, api_response, openai_key) uses the LLM to produce a human-readable, structured answer.
If the response is very large, it uses the chunked path analyze_response_chunked(...) and then synthesizes a final answer.
The response and a summary are saved back into KnowledgeStore for future cache hits.
Where the information actually comes from
Primary data source: Live WHINT API (when cache miss or fresh data needed).
Secondary data source: KnowledgeStore cache (returns prior results instantly if available).
Prompt context only (not answer content):
ApiCallMaster/src/prompt_builder.py may include a small sample of interface names from ApiCallMaster/all_interface_names.txt to ground the LLM’s behavior.
Inventory types are pulled from ApiCallMaster/src/inventory_types.py for routing rules.
Not used for answers at runtime:
PDFs in ApiCallMaster/assets/attached_assets/ are not programmatically parsed; they inform prompt design, not the data returned.
systemprompt.txt is not wired into the flow; the new prompt builder is used instead.
knowledge_entities/*.jsonl is not read in the main UI flow.
methods/* modules (graph_rag, vector_rag, etc.) are present but not invoked by the Streamlit app’s current path.
methods/llm_synthesis.py is wired to use the builder but isn’t called by app.py in the normal chat flow.
LLM usage points
Query generation: LLM called with a system prompt from prompt_builder to produce the JSON query.
Analysis/summarization: LLM used to turn API (or cached) data into a concise, structured answer; chunking used if needed.
Credentials and providers
LLMProviderManager selects and calls providers (OpenAI, Gemini, Anthropic, Groq, OpenRouter), initialized from your stored credentials.
WHINT API credentials (base URL, x-api-key, username, password) are used to make authenticated POST requests.

## Knowledgestore vs cache

’ll open KnowledgeStore to be precise about behavior, then summarize the differences and overlaps.
What it is
KnowledgeStore: An on-disk caching system for WHINT API query results plus a persistent “entity strings” store.
Cache (within KnowledgeStore): The time-bounded part that stores responses and summaries keyed by query+endpoint.
When it’s used
Before calling the API: app checks KnowledgeStore for an exact cache hit; on miss, tries a fuzzy/similar match; on miss, calls API and then saves into cache.
After API call: stores a compact summary, chunk summaries, and entity strings; updates the index.
Where it lives
Cache files: knowledge_cache/ with index.json plus one .json per cached entry.
Persistent entity lines: knowledge_entities/ one .jsonl per endpoint (e.g., aggregated names/IDs); separate from the TTL cache.
How it works
Cache key: Hash of normalized query + endpoint to reduce misses from cosmetic ordering.
Validity: Entries expire after 30 days (config in KnowledgeStore.max_age_days).
Retrieval: exact match → valid? return; else fuzzy match (field overlap similarity) → return if above threshold.
Persistence: Entity strings appended to endpoint-specific .jsonl files and do not expire automatically.
Why both exist
Cache: Fast reuse of full responses/summaries to avoid repeat API calls and LLM work.
Persistent entity store: Durable, growing factual crumbs (names/ids/keys) for grounding and recall even after cache entries expire.
How they differ
Lifetime: Cache expires (30 days); entity store is durable (no TTL).
Content: Cache stores structured response metadata, summaries, and some data; entity store stores deduplicated compact lines per entity.
Usage path: Cache is the first stop for answering; entity store is used to enrich/supplement prompts/analysis (and aggregate views) but not as a drop-in for full responses.
How they are similar
Both are on-disk, JSON-based, and keyed or grouped by endpoint.
Both reduce external calls and LLM load by reusing prior work.
Which one powers your answers
Primary: Cache hit returns previous processed summary or raw summary-derived data.
Secondary: If no exact cache, aggregate cached entries and persistent entity lines can be fused to produce an answer without a new API call.
Fallback: Live API call, then cache is updated for next time.
Are they permanent
Cache: No, expires after 30 days and is cleaned up.
Entity store: Yes (practically), persists until manually deleted.
What happens if something is missing
No cache and no useful aggregate → app calls WHINT API; results are analyzed and saved back to cache and entity store.
Where in code
Implementation: ApiCallMaster/src/knowledge_store.py.
Integration: used across app.py for get/store, fuzzy match, aggregate summaries, and persistent entity I/O.
When to adjust
Increase TTL if you want fewer expirations.
Tune fuzzy similarity threshold to prefer reuse vs freshness.
Purge entity store if it grows too large or you want a clean slate.

## Endpoint connection (example)

```python
response = requests.post(
    f"{api_url_str}/interfaces",
    headers=headers,
    auth=(username_str, password_str),
    json=test_query,
    timeout=10
)
```

## Endpoints

Interfaces (general default)
${BASE_URL}/interfaces
Interfaces (type-optimized routing)
${BASE_URL}/interfaces/sap (types 14–20)
${BASE_URL}/interfaces/mule (types 0–1)
${BASE_URL}/interfaces/azure (types 3–8)
${BASE_URL}/interfaces/apim (type 2)
Inventory (entity-based general, including relationships via with)
${BASE_URL}/inventory (entity=inventory without type shortcuts)
${BASE_URL}/inventory/upsert (root upsert for inventory)
Tasks
${BASE_URL}/tasks (entity=task; supports with=runs and filters)
${BASE_URL}/tasks/upsert (if you send upsert for task)
Logs
${BASE_URL}/logs (entity=logEntry)
Datasources
${BASE_URL}/datasources (entity=datasource)
${BASE_URL}/datasources/upsert (if you send upsert for datasource)
Systems
${BASE_URL}/systems (entity=system)
${BASE_URL}/systems/upsert (if you send upsert for system)
Dataflows
${BASE_URL}/dataflows (entity=dataFlow)
${BASE_URL}/dataflows/upsert (if you send upsert for dataFlow)

## Usage examples (selected)

Here are 30 concrete question types your app can answer now, organized by endpoint.
Interfaces (inventory + type routing)
Show interfaces where name contains “Connect”.
List SAP interfaces (ODATA/SOAP/EventMesh/IDoc/etc.).
List MULE applications/APIs.
Show Azure interfaces (APIM/EventGrid/Logic Apps/Service Bus).
Show APIM interfaces only.
Get interfaces excluding EAM/PLANNED types.
Find interfaces by sender or receiver name.
Find interfaces where sender or receiver datasource name is “X”.
Get interfaces with metadata included.
Get interfaces with properties included.
Get interfaces with tags included.
Return interfaces with objects included.
Top 100 interfaces by last_traffic or recent change (if field available).
Interfaces connected to a specific system (e.g., SAP NetWeaver).
Tasks
List all tasks with failed runs.
List tasks that succeeded in the last N days (if data available).
Get tasks and include their runs with duration > X.
Count tasks by data_source_id “X”.
Show tasks that have no runs in the last N days (possible via filters).
Logs
Show all log entries.
Show log entries at level >= 2 (if supported).
Show recent log entries (by create_time) for the last N days.
Find log entries containing “failed” or “error” in message.
Datasources, Systems, Dataflows
List all datasources and their names.
Show interfaces where the datasource is “CPI CF FreeTier”.
List all systems and filter by name containing “SAP”.
List dataflows and filter by name containing “sync” (if present).
Combined/Advanced filters
Inventory where sender OR receiver has datasource name “X”.
Inventory where metadata “Adapter” = “HTTP” (via with/metadata filter).
Inventory where properties include type_id = “X”.
Interfaces tagged with “DE” and name like “API”.

## Performance

- Cache TTL: 30 days; high reuse with normalized keys
- Intent detection accuracy: ~95.7% (tests)
- Cached responses: sub-second to ~2s; live API + LLM: typically 5–15s

## Troubleshooting

- Credentials failing: confirm env/secrets precedence; test base URL reachability
- Cache not updating: use `clear_cache.py` or delete `knowledge_cache/` entries
- LLM timeouts: provider failover is automatic; verify keys and quotas

## Development & Testing

Run useful tests/scripts:

```bash
python test_user_intent_standalone.py
python test_cache_improvements.py
python test_enhanced_entity_extraction.py
```

Utilities:
- `clear_cache.py` / `.bat` – clear TTL cache
- `cleanup_pycache.py` / `.bat` – remove __pycache__
- `list_all_interfaces.py` – extract names from data

## Deployment

See `deployment/` for Docker, docker-compose, and Kubernetes manifests.

---

For deeper docs, see:
- `docs/architecture.md`
- `docs/API_KEY_SETUP_GUIDE.md`
- `docs/ENDPOINT_ROUTING_EXAMPLES.md`
- `docs/KNOWLEDGE_STORAGE_APPROACH.md`
- `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`
- `INTENT_BASED_RESPONSES.md`