# DuckDB Local Engine

This module provides a high-performance local execution engine for WHINT Integration Cockpit queries using DuckDB. It translates WHINT JSON queries to SQL and executes them against a local database created from your JSON data.

## Features

- **High Performance**: DuckDB provides fast SQL execution on large datasets
- ****: No caching - always executes against current data
- **Query Translation**: Converts WHINT JSON queries to optimized SQL
- **Rich Schema Support**: Handles complex nested data (metadata, properties, tags)
- **Diagnostics**: Built-in debugging and diagnostic capabilities

## Components

### `loader.py`
Manages database creation and refresh from JSON files.

```python
from duckdb.loader import DuckDBLoader

loader = DuckDBLoader("duckdb/wic.duckdb")
success = loader.load_from_json("23-09-2025.json", force_refresh=True)
```

**Features:**
- Auto-detects JSON shape (array, NDJSON, object)
- Creates normalized views for easy querying
- Handles large files with streaming ingestion
- Provides database statistics and validation

### `translator.py`
Converts WHINT JSON queries to DuckDB SQL.

```python
from duckdb.translator import DuckDBTranslator

translator = DuckDBTranslator()
sql, params = translator.translate(whint_query)
```

**Supported Query Features:**
- Entity mapping (`inventory` → `inventory_view`)
- Field selection and projection
- WHERE conditions with operators (`eq`, `like`, `in`, etc.)
- Type normalization (MULE/SAP/AZURE/APIM → numeric IDs)
- `with` clauses for metadata/properties/tags
- `limit`/`offset` pagination

### `executor.py`
Executes SQL queries and returns API-shaped responses.

```python
from duckdb.executor import DuckDBExecutor

executor = DuckDBExecutor("duckdb/wic.duckdb")
result = executor.execute_query(whint_query)
```

**Features:**
- SQL execution with parameter binding
- API response formatting
- Error handling and diagnostics
- Type distribution analysis

## Database Schema

### `raw_all` Table
Contains the raw ingested data with columns:
- `name`: Interface name
- `type`: Interface type (string)
- `description`: Interface description
- `metadata`: Array of metadata objects
- `properties`: Array of property objects
- `tags`: Array of tag objects
- `sender`: Sender object
- `receiver`: Receiver object

### `inventory_view` View
Normalized view for inventory queries:
- `norm_name`: Normalized name
- `norm_type`: Normalized type
- `norm_description`: Normalized description
- `norm_sender_name`: Extracted sender name
- `norm_receiver_name`: Extracted receiver name
- `metadata`, `properties`, `tags`, `sender`, `receiver`: Original complex fields

## Usage Examples

### Basic Query Translation

```python
whint_query = {
    "query": {
        "entity": "inventory",
        "fields": ["name", "type", "description"],
        "where": [{
            "option": 1,
            "conditions": [{
                "field": {
                    "name": "type",
                    "eq": "21"
                }
            }]
        }],
        "limit": 10
    }
}

# Translate to SQL
translator = DuckDBTranslator()
sql, params = translator.translate(whint_query)
print(f"SQL: {sql}")
print(f"Params: {params}")
```

### Execute Query

```python
executor = DuckDBExecutor()
result = executor.execute_query(whint_query)
print(f"Found {result['total']} items")
```

### Get Diagnostics

```python
diagnostics = executor.get_diagnostics(whint_query)
print(f"Type distribution: {diagnostics['type_distribution']}")
print(f"Sample data: {diagnostics['sample_data']}")
```

## Query Translation Rules

### Entity Mapping
- `inventory` → `inventory_view`
- `task` → `raw_all` (TODO: create `task_view`)
- `logEntry` → `raw_all` (TODO: create `log_view`)
- `datasource` → `raw_all` (TODO: create `datasource_view`)
- `system` → `raw_all` (TODO: create `system_view`)
- `dataFlow` → `raw_all` (TODO: create `dataflow_view`)

### Field Mapping
For inventory queries:
- `name` → `norm_name`
- `type` → `norm_type`
- `description` → `norm_description`
- `sender_name` → `norm_sender_name`
- `receiver_name` → `norm_receiver_name`
- `metadata` → `metadata`
- `properties` → `properties`
- `tags` → `tags`

### Type Normalization
String type labels are converted to numeric IDs:
- `"MULE"` → `1`
- `"SAP_IDOC"` → `21`
- `"SAP_IS_APIM"` → `23`
- etc.

### WHERE Conditions
Supported operators:
- `eq` → `=`
- `ne` → `!=`
- `gt` → `>`
- `gte` → `>=`
- `lt` → `<`
- `lte` → `<=`
- `like` → `ILIKE` (with wildcards)
- `in` → `IN`
- `not_in` → `NOT IN`

## Performance Tips

1. **Use Views**: Always query `inventory_view` instead of `raw_all` for better performance
2. **Limit Results**: Use `limit` to avoid processing large result sets
3. **Index on Type**: DuckDB automatically optimizes queries on `norm_type`
4. **Batch Operations**: For multiple queries, reuse the same connection

## Error Handling

The executor provides detailed error information:
- Invalid query structure
- SQL execution errors
- Missing database files
- Type resolution failures

## CLI Usage

### Load Data
```bash
# Load JSON into DuckDB
uv run python duckdb/loader.py --input 23-09-2025.json --db duckdb/wic.duckdb

# Force refresh existing database
uv run python duckdb/loader.py --input 23-09-2025.json --db duckdb/wic.duckdb --force
```

### Database Info
```bash
# Show database information
uv run python duckdb/loader.py --db duckdb/wic.duckdb --info

# Validate database
uv run python duckdb/loader.py --db duckdb/wic.duckdb --validate
```

## Integration with Main App

The DuckDB engine integrates with the main Streamlit app as a third data source option:

1. **UI Toggle**: "Local Engine (DuckDB)" in data source selector
2. ****: No caching - always executes against current data
3. **Same Interface**: Uses same WHINT query format as API and Local JSON modes
4. **Diagnostics**: Built-in debugging for query issues

## Future Enhancements

- [ ] Create specialized views for tasks, logs, datasources, systems, dataflows
- [ ] Add support for write operations (upsert queries)
- [ ] Implement query optimization and caching
- [ ] Add support for complex joins and aggregations
- [ ] Create Parquet export for faster loading
- [ ] Add support for incremental updates
