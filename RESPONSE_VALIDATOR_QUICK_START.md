# 🚀 Response Validator - Quick Start Guide

## What Is It?

A **validation agent** that automatically detects if your application generated an incorrect response, regardless of which method was used (vector_rag, graph_rag, db_lookup, llm_synthesis).

## How I Found The Error (Your Example)

When you asked "how did you find out this answer is not correct?", I showed you **6 pieces of evidence**:

1. ❌ Generated query showed `"eq": "13"` (numeric ID) instead of `"in": ["SAP_IS_APIM"]`
2. ❌ SQL had `LIMIT 300` when you asked for "all"
3. ❌ SQL had **no WHERE clause** at all
4. ❌ SQL parameters were **empty** `{}`
5. ❌ Got exactly 300 records instead of ~291 APIM interfaces
6. ❌ Results contained **mixed types** (24, 21, SAP_PO) instead of only APIM types

**All 6 pointed to**: Old code still running → Need restart

## What The Agent Needs To Know

### 1. Expected Behavior Patterns

```python
# Correct type filter
{
  "name": "type",
  "in": ["SAP_IS_APIM", "APIM", "AZURE_APIM"]  # ✅ String names
}

# Incorrect type filter (old code)
{
  "name": "norm_type",  # ❌ Deprecated field
  "eq": "13"  # ❌ Numeric ID
}
```

### 2. Error Signatures

```python
error_signatures = {
  "ERR_OLD_TYPE_FILTER": {
    "symptoms": ["eq: 13", "norm_type"],
    "diagnosis": "NLP processor using old code",
    "fix": "Restart Streamlit app"
  },
  "ERR_DEFAULT_LIMIT": {
    "symptoms": ["LIMIT 300", "user said 'all'"],
    "diagnosis": "Translator using old code",
    "fix": "Restart Streamlit app"
  },
  "ERR_MISSING_WHERE": {
    "symptoms": ["No WHERE clause", "empty params"],
    "diagnosis": "Filter not applied",
    "fix": "Check translator logic"
  }
}
```

### 3. Cross-Validation Rules

| Check | Against | Red Flag |
|-------|---------|----------|
| Generated Query | User Query | User says "APIM", query has type=13 |
| SQL | Generated Query | Query has where[], SQL has no WHERE |
| Results Count | Diagnostics | Expected 291, got 300 |
| Results Types | User Query | Asked APIM, got SAP_PO |

## Quick Usage

### Installation

```bash
# Files are already created:
# - src/response_validator.py (main validator)
# - examples/response_validator_usage.py (examples)
# - RESPONSE_VALIDATION_AGENT_DESIGN.md (full design)
```

### Basic Usage

```python
from src.response_validator import ResponseValidator

# Initialize
validator = ResponseValidator()

# After executing your query
response_data = {
    "generated_query": generated_query,
    "sql_query": sql,
    "sql_params": params,
    "results": results,
    "diagnostics": diagnostics
}

# Validate
result = validator.validate_response(
    user_query="Show all APIM interfaces",
    method_name="db_lookup",
    response_data=response_data
)

# Check
if not result.is_valid:
    print("❌ VALIDATION FAILED")
    for issue in result.issues:
        print(f"  - {issue.message}")
        print(f"    Fix: {issue.fix}")
```

### Streamlit Integration

```python
# In your app.py
from src.response_validator import ResponseValidator

validator = ResponseValidator()

# After query execution
validation = validator.validate_response(
    user_query=user_question,
    method_name="db_lookup",
    response_data=response_data
)

# Show in UI
if not validation.is_valid:
    st.error("⚠️ Response Validation Failed!")
    
    with st.expander("🔍 See Issues"):
        for issue in validation.issues:
            st.markdown(f"**{issue.message}**")
            st.code(issue.fix)
    
    if validation.recommended_action == "RESTART_APPLICATION":
        st.error("🔄 Please restart the app (CTRL+C)")
else:
    st.success("✅ Response Validated")
```

## What It Detects

### For DB Lookup (DuckDB)

✅ Checks:
- Type filter format (string vs numeric)
- LIMIT clause appropriateness
- WHERE clause presence
- Parameter binding
- Result count vs diagnostics
- Type distribution in results

### For Vector RAG

✅ Checks:
- Chunk relevance (similarity scores)
- Result count
- Empty results when data should exist

### For Graph RAG

✅ Checks:
- Seed entity extraction
- Neighborhood size
- Cypher query generation

### For LLM Synthesis

✅ Checks:
- Prompt quality
- Context completeness
- Hallucination markers

## Examples

### Example 1: Detecting Old Code

```python
# Run the example
python examples/response_validator_usage.py
```

**Output:**
```
✅ Validation Complete!
   Is Valid: False
   Confidence: 0.0
   Status: CRITICAL_FAILURE
   Recommended Action: RESTART_APPLICATION

🔍 Issues Found (2):

   1. [CRITICAL] ERR_OLD_TYPE_FILTER
      Message: Type filter using numeric ID instead of string name
      Expected: String type name (e.g., 'SAP_IS_APIM')
      Actual: Numeric ID: 13
      Fix: Restart Streamlit app - NLP processor module not reloaded

   2. [CRITICAL] ERR_DEFAULT_LIMIT
      Message: User asked for all results but SQL has default LIMIT 300
      Expected: No LIMIT clause (to get complete results)
      Actual: LIMIT 300 present in SQL
      Fix: Restart Streamlit app - Translator module not reloaded
```

### Example 2: Correct Response

```python
result = validate_response(
    user_query="Show all APIM interfaces",
    method_name="db_lookup",
    response_data=correct_response
)

print(result['is_valid'])  # True
print(result['issues'])    # []
```

## Validation Report Structure

```json
{
  "is_valid": false,
  "confidence": 0.0,
  "overall_status": "CRITICAL_FAILURE",
  "recommended_action": "RESTART_APPLICATION",
  "issues": [
    {
      "severity": "CRITICAL",
      "type": "ERR_OLD_TYPE_FILTER",
      "message": "Type filter using numeric ID",
      "expected": "String type name",
      "actual": "Numeric ID: 13",
      "fix": "Restart Streamlit app",
      "confidence": 0.0
    }
  ],
  "evidence": [
    {
      "location": "generated_query.where",
      "snippet": "{\"name\": \"norm_type\", \"eq\": \"13\"}"
    }
  ],
  "cross_validation_results": {
    "user_query_vs_generated_query": "FAIL",
    "generated_query_vs_sql": "FAIL",
    "results_vs_diagnostics": "FAIL"
  },
  "diagnostic_summary": {
    "expected_result_count": 291,
    "actual_result_count": 300,
    "modules_not_reloaded": ["src.nlp_processor", "duckdb_engine.translator"]
  }
}
```

## Recommended Actions

The validator suggests specific actions:

| Action | When | What To Do |
|--------|------|------------|
| `RESTART_APPLICATION` | Old code detected | CTRL+C and restart Streamlit |
| `CHECK_CONFIGURATION` | Missing data/context | Check env vars, API keys |
| `REINGEST_DATA` | Data quality issues | Re-run data ingestion |
| `REFORMULATE_QUERY` | No results found | Rephrase the query |
| `REVIEW_ISSUES` | Minor warnings | Check logs, non-critical |
| `NONE` | All good | No action needed ✅ |

## Files Created

1. **`src/response_validator.py`** (438 lines)
   - Main validation logic
   - ResponseValidator class
   - ValidationResult and ValidationIssue classes

2. **`examples/response_validator_usage.py`** (340 lines)
   - 5 complete examples
   - Integration patterns
   - Test cases

3. **`RESPONSE_VALIDATION_AGENT_DESIGN.md`** (1000+ lines)
   - Complete design document
   - Knowledge base structure
   - Error signature database
   - Cross-validation matrix

4. **`RESPONSE_VALIDATOR_QUICK_START.md`** (this file)
   - Quick reference
   - Usage examples
   - Integration guide

## Advanced: Auto-Healing

Future enhancement - automatically retry with different settings:

```python
# Future feature
if not validation.is_valid:
    if validation.recommended_action == "REFORMULATE_QUERY":
        # Try with different method
        result = try_with_vector_rag(user_query)
    elif validation.recommended_action == "RESTART_APPLICATION":
        # Auto-reload modules (if possible)
        reload_modules()
```

## Testing The Validator

```bash
# Run all examples
python examples/response_validator_usage.py

# Expected output:
# - Example 1: Detects old code (FAIL)
# - Example 2: Validates correct response (PASS)
# - Example 3: Checks vector RAG (WARNINGS)
# - Example 4: Shows integration code
# - Example 5: Automated batch validation
```

## Key Benefits

1. **Automatic Error Detection**: No manual checking needed
2. **Actionable Fixes**: Tells you exactly what to do
3. **Multi-Method Support**: Works with all query methods
4. **Cross-Validation**: Checks consistency across pipeline stages
5. **Confidence Scoring**: Prioritizes critical issues
6. **Evidence Tracking**: Shows exactly where the problem is

## Integration Checklist

- [ ] Import `ResponseValidator` in your app
- [ ] Initialize validator once (at app start)
- [ ] Collect response_data after each query
- [ ] Call `validate_response()` before showing results
- [ ] Display validation status in UI
- [ ] Show issues and fixes if validation fails
- [ ] Take recommended action

## Next Steps

1. **Test It**: Run `examples/response_validator_usage.py`
2. **Integrate**: Add to your `app.py` (see Example 4)
3. **Monitor**: Check validation results in production
4. **Extend**: Add custom validation rules as needed

---

## Summary

You asked: *"Can I use this info to create an agent which says generated response is incorrect?"*

**Answer**: ✅ **YES!** 

The agent:
- ✅ Knows expected behavior patterns
- ✅ Has error signature database
- ✅ Performs cross-validation
- ✅ Scores confidence
- ✅ Suggests specific fixes
- ✅ Works with all methods

**Result**: Automatic validation with actionable recommendations! 🎉

---

**Questions?** Check `RESPONSE_VALIDATION_AGENT_DESIGN.md` for full details.


