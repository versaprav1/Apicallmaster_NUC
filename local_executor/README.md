Local JSON Query Executor
=========================

Purpose
-------
Execute WHINT-style JSON queries locally against a large JSON file (e.g., 23-09-2025.json) without calling the remote API.

Components
----------
- loader.py: Streaming iterator over large JSON arrays (ijson preferred; falls back to json.load).
- schema.py: Heuristic entity detection to separate inventory/tasks/logs.
- router.py: Maps routed endpoint to a stream of matching records.
- executor.py: Applies where/fields/with/limit/offset to selected records.
- adapters.py: Shapes results to match the API contract ({"data": [...]}).

Supported Query Features
------------------------
- entity selection via routed endpoint
- where with option 0/1 (AND/OR)
- operators: eq, ne, like, gt, lt, gte, lte
- nested entity predicates using dotted paths (e.g., sender.data_source_id)
- with to include embedded sections (metadata, properties, tags, sender, receiver)
- fields projection, limit and offset

Usage (integration)
-------------------
1. Decide data source (API vs Local JSON) in the UI.
2. If Local JSON, open the file path and iterate records via loader.iter_records.
3. Use existing determine_api_endpoint(query, base_url) to get the logical endpoint.
4. Stream-filter records with router.select_collection and executor.execute_query.
5. Return adapters.to_api_response to the app as if it came from the API.

Notes
-----
- For very large files, prefer ijson to avoid memory pressure.
- You can later swap to DuckDB/Polars for higher performance without changing the UI.


