"""
Response Validator - Usage Examples

Shows how to integrate the Response Validator into your application
to automatically detect incorrect responses.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.response_validator import ResponseValidator, validate_response
import json


def example_1_db_lookup_validation():
    """Example: Validating a DB Lookup response"""
    
    print("=" * 80)
    print("EXAMPLE 1: DB Lookup Validation - Detecting Old Code")
    print("=" * 80)
    
    # Simulate a response with old code (numeric type IDs)
    user_query = "Show all APIM interfaces"
    method_name = "db_lookup"
    
    response_data = {
        "generated_query": {
            "query": {
                "entity": "inventory",
                "fields": ["name", "type", "description"],
                "where": [{
                    "option": 1,
                    "conditions": [{
                        "field": {
                            "name": "norm_type",  # ❌ Should be "type"
                            "eq": "13"  # ❌ Should be "SAP_IS_APIM"
                        }
                    }]
                }],
                "limit": 300  # ❌ Should be omitted for "all"
            }
        },
        "sql_query": "SELECT name, type, description FROM interfaces LIMIT 300",  # ❌ No WHERE clause!
        "sql_params": {},  # ❌ Should have parameters
        "results": [{"name": "Interface1", "type": "24"}, {"name": "Interface2", "type": "21"}] * 150,  # 300 results
        "diagnostics": {
            "type_distribution": {
                "SAP_IS_APIM": 291,
                "SAP_ODATA": 150,
                "SAP_SOAP": 100
            }
        },
        "execution_time": 0.5
    }
    
    # Validate
    validator = ResponseValidator()
    result = validator.validate_response(user_query, method_name, response_data)
    
    # Print results
    print(f"\n✅ Validation Complete!")
    print(f"   Is Valid: {result.is_valid}")
    print(f"   Confidence: {result.confidence}")
    print(f"   Status: {result._get_status()}")
    print(f"   Recommended Action: {result.recommended_action}")
    
    print(f"\n🔍 Issues Found ({len(result.issues)}):")
    for i, issue in enumerate(result.issues, 1):
        print(f"\n   {i}. [{issue.severity}] {issue.issue_type}")
        print(f"      Message: {issue.message}")
        print(f"      Expected: {issue.expected}")
        print(f"      Actual: {issue.actual}")
        print(f"      Fix: {issue.fix}")
    
    print(f"\n📊 Diagnostic Summary:")
    print(json.dumps(result.diagnostic_summary, indent=2))
    
    return result


def example_2_correct_response():
    """Example: Validating a CORRECT response"""
    
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: DB Lookup Validation - Correct Response")
    print("=" * 80)
    
    user_query = "Show all APIM interfaces"
    method_name = "db_lookup"
    
    response_data = {
        "generated_query": {
            "query": {
                "entity": "inventory",
                "fields": ["name", "type", "description"],
                "where": [{
                    "option": 1,
                    "conditions": [{
                        "field": {
                            "name": "type",  # ✅ Correct
                            "in": ["SAP_IS_APIM", "APIM", "AZURE_APIM"]  # ✅ String names
                        }
                    }]
                }]
                # ✅ No limit for "all"
            }
        },
        "sql_query": "SELECT name, type, description FROM interfaces WHERE CAST(type AS VARCHAR) IN (?, ?, ?)",  # ✅ Has WHERE
        "sql_params": {
            "param_0_0": "SAP_IS_APIM",
            "param_0_1": "APIM",
            "param_0_2": "AZURE_APIM"
        },  # ✅ Parameters bound
        "results": [{"name": f"APIM_Interface_{i}", "type": "SAP_IS_APIM"} for i in range(291)],  # 291 results
        "diagnostics": {
            "type_distribution": {
                "SAP_IS_APIM": 291,
                "SAP_ODATA": 150,
                "SAP_SOAP": 100
            }
        },
        "execution_time": 0.8
    }
    
    # Validate using quick function
    result_dict = validate_response(user_query, method_name, response_data)
    
    print(f"\n✅ Validation Complete!")
    print(f"   Is Valid: {result_dict['is_valid']}")
    print(f"   Confidence: {result_dict['confidence']}")
    print(f"   Status: {result_dict['overall_status']}")
    print(f"   Issues Found: {len(result_dict['issues'])}")
    
    if result_dict['issues']:
        print(f"\n⚠️  Warnings:")
        for issue in result_dict['issues']:
            print(f"   - [{issue['severity']}] {issue['message']}")
    else:
        print(f"\n🎉 No issues found - Response is valid!")


def example_3_vector_rag_validation():
    """Example: Validating a Vector RAG response"""
    
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Vector RAG Validation")
    print("=" * 80)
    
    user_query = "Find interfaces related to customer data"
    method_name = "vector_rag"
    
    response_data = {
        "chunks": [
            {"content": "Customer interface 1", "similarity": 0.85},
            {"content": "Customer interface 2", "similarity": 0.78},
            {"content": "Customer interface 3", "similarity": 0.25},  # ❌ Low similarity
            {"content": "Unrelated interface", "similarity": 0.15},  # ❌ Low similarity
            {"content": "Another low match", "similarity": 0.10}  # ❌ Low similarity
        ],
        "execution_time": 2.3
    }
    
    validator = ResponseValidator()
    result = validator.validate_response(user_query, method_name, response_data)
    
    print(f"\n✅ Validation Complete!")
    print(f"   Is Valid: {result.is_valid}")
    print(f"   Issues: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"\n   ⚠️  [{issue.severity}] {issue.message}")
        print(f"      Fix: {issue.fix}")


def example_4_integration_in_app():
    """Example: How to integrate in your app.py"""
    
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Integration in Streamlit App")
    print("=" * 80)
    
    code_example = '''
# In your app.py or methods/*.py

from src.response_validator import ResponseValidator

# Initialize validator once
validator = ResponseValidator()

# After executing your query (DB lookup, Vector RAG, etc.)
response_data = {
    "user_query": user_question,
    "generated_query": generated_query,
    "sql_query": sql,
    "sql_params": params,
    "results": results,
    "diagnostics": diagnostics,
    "execution_time": execution_time
}

# Validate the response
validation_result = validator.validate_response(
    user_query=user_question,
    method_name="db_lookup",  # or "vector_rag", "graph_rag", etc.
    response_data=response_data
)

# Show validation in UI
if not validation_result.is_valid:
    st.error("⚠️ Response Validation Failed!")
    st.warning(f"Confidence: {validation_result.confidence:.0%}")
    
    with st.expander("🔍 Validation Issues"):
        for issue in validation_result.issues:
            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }.get(issue.severity, "⚪")
            
            st.markdown(f"{severity_emoji} **{issue.message}**")
            st.markdown(f"   - Expected: `{issue.expected}`")
            st.markdown(f"   - Actual: `{issue.actual}`")
            st.markdown(f"   - **Fix**: {issue.fix}")
    
    # Show recommended action
    if validation_result.recommended_action == "RESTART_APPLICATION":
        st.error("🔄 **ACTION REQUIRED**: Restart the Streamlit app")
        st.code("CTRL+C in terminal, then restart")
else:
    st.success("✅ Response Validated Successfully")
    if validation_result.issues:
        st.info(f"ℹ️ {len(validation_result.issues)} warnings (non-critical)")

# Continue with displaying results...
st.write(results)
'''
    
    print("\n📝 Integration Code:")
    print(code_example)


def example_5_automated_response_check():
    """Example: Automatically check all responses"""
    
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: Automated Response Checking")
    print("=" * 80)
    
    # Simulate multiple query responses
    test_cases = [
        {
            "name": "Correct APIM Query",
            "user_query": "Show APIM interfaces",
            "method": "db_lookup",
            "data": {
                "generated_query": {"query": {"entity": "inventory", "where": [{"option": 1, "conditions": [{"field": {"name": "type", "in": ["SAP_IS_APIM"]}}]}]}},
                "sql_query": "SELECT * FROM interfaces WHERE type IN (?)",
                "sql_params": {"param_0_0": "SAP_IS_APIM"},
                "results": [{"name": "Test", "type": "SAP_IS_APIM"}] * 291,
                "diagnostics": {"type_distribution": {"SAP_IS_APIM": 291}}
            }
        },
        {
            "name": "Old Code Detected",
            "user_query": "List all SAP interfaces",
            "method": "db_lookup",
            "data": {
                "generated_query": {"query": {"entity": "inventory", "where": [{"option": 1, "conditions": [{"field": {"name": "norm_type", "eq": "24"}}]}], "limit": 300}},
                "sql_query": "SELECT * FROM interfaces LIMIT 300",
                "sql_params": {},
                "results": [{"name": "Test", "type": "24"}] * 300,
                "diagnostics": {"type_distribution": {"SAP_ODATA": 450}}
            }
        }
    ]
    
    validator = ResponseValidator()
    
    print("\n📊 Validation Summary:")
    print("-" * 80)
    
    for test in test_cases:
        result = validator.validate_response(test["user_query"], test["method"], test["data"])
        
        status_emoji = "✅" if result.is_valid else "❌"
        print(f"\n{status_emoji} {test['name']}")
        print(f"   Valid: {result.is_valid} (Confidence: {result.confidence:.0%})")
        print(f"   Issues: {len(result.issues)}")
        
        if result.issues:
            for issue in result.issues[:2]:  # Show first 2 issues
                print(f"   - {issue.message}")


if __name__ == "__main__":
    # Run all examples
    example_1_db_lookup_validation()
    example_2_correct_response()
    example_3_vector_rag_validation()
    example_4_integration_in_app()
    example_5_automated_response_check()
    
    print("\n\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)

