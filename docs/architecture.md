# WHINT API AI Assistant – Architecture (Light Theme)

This page summarizes the end-to-end pipeline and main components, including the optional Local JSON path and a future DuckDB/Polars branch.

## High-level flow

1. UI (Streamlit `app.py`)
   - Source selector: API or Local JSON
   - Presets and question input
2. LLM Prompting (`src/prompt_builder.py`) → NL to WHINT JSON query
3. Endpoint Routing (`app.py`)
   - Interfaces (/interfaces, /interfaces/sap|mule|azure|apim)
   - Tasks (/tasks), Logs (/logs), Datasources (/datasources), Systems (/systems), Dataflows (/dataflows)
4. Execution Path
   - API mode: HTTP POST to routed endpoint
   - Local mode: `local_executor/` reads JSON and executes filters
   - (Optional) DuckDB/Polars: future local engine
5. KnowledgeStore (`src/knowledge_store.py`)
   - Cache + fuzzy-match + persistent entity strings
6. Analysis
   - LLM analysis or chunked → synthesis
7. Output to UI

## Components (by module)

- `app.py`
  - UI, source selector, query creation, endpoint routing
  - Branch to API or Local JSON execution
- `src/prompt_builder.py`
  - System prompts for translation and synthesis
- `src/llm_providers.py`
  - Provider selection and LLM invocation
- `src/knowledge_store.py`
  - Cache, fuzzy match, persistent entity store
- `local_executor/`
  - `loader.py`: stream large JSON/NDJSON
  - `router.py`: map routed endpoint to collection
  - `executor.py`: apply where/fields/with/limit/offset; type normalization
  - `schema.py`: heuristic entity detection
  - `adapters.py`: return API-shaped response
- (Future) Local Engine
  - DuckDB/Polars execution for large data

## Diagram (Excalidraw)

The diagram is provided as an Excalidraw scene (light theme):

- File: `ApiCallMaster/docs/flow-architecture.excalidraw`
- Export: Open the `.excalidraw` in Excalidraw and export PNG/SVG as needed.

Key swimlanes: UI → LLM → Router → (API | Local Executor | DuckDB/Polars) → KnowledgeStore → Analyzer → UI.

## Notes

- Local JSON mode bypasses cache-first on execution, then stores results back to cache.
- Type normalization expands group shorthands (MULE/SAP/AZURE/APIM/OTHER) and accepts labels or numeric IDs.
- Zero-result diagnostics can hint at type distribution in local files.
