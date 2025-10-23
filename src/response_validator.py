"""
Response Validation Agent

Automatically validates if generated responses are correct across all methods
(vector_rag, graph_rag, db_lookup, llm_synthesis, API).

Uses pattern matching, cross-validation, and error signature detection
to identify incorrect responses and suggest fixes.
"""

from typing import Dict, Any, List, Optional, Set
import re
from datetime import datetime


class ValidationIssue:
    """Represents a single validation issue"""
    
    def __init__(
        self,
        severity: str,
        issue_type: str,
        message: str,
        expected: str = "",
        actual: str = "",
        fix: str = "",
        confidence: float = 1.0
    ):
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.issue_type = issue_type  # Error signature ID
        self.message = message
        self.expected = expected
        self.actual = actual
        self.fix = fix
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "type": self.issue_type,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "fix": self.fix,
            "confidence": self.confidence
        }


class ValidationResult:
    """Complete validation result"""
    
    def __init__(self, method_name: str):
        self.method_name = method_name
        self.is_valid = True
        self.confidence = 1.0
        self.issues: List[ValidationIssue] = []
        self.evidence: List[Dict[str, str]] = []
        self.cross_validation_results: Dict[str, str] = {}
        self.recommended_action: Optional[str] = None
        self.diagnostic_summary: Dict[str, Any] = {}
    
    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue"""
        self.issues.append(issue)
        if issue.severity in ["CRITICAL", "HIGH"]:
            self.is_valid = False
            self.confidence = min(self.confidence, issue.confidence)
    
    def add_evidence(self, location: str, snippet: str):
        """Add evidence for issues"""
        self.evidence.append({"location": location, "snippet": snippet})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "method_name": self.method_name,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "overall_status": self._get_status(),
            "issues": [issue.to_dict() for issue in self.issues],
            "evidence": self.evidence,
            "cross_validation_results": self.cross_validation_results,
            "recommended_action": self.recommended_action,
            "diagnostic_summary": self.diagnostic_summary
        }
    
    def _get_status(self) -> str:
        """Get overall status based on issues"""
        if not self.is_valid:
            critical_count = sum(1 for i in self.issues if i.severity == "CRITICAL")
            if critical_count > 0:
                return "CRITICAL_FAILURE"
            return "VALIDATION_FAILED"
        
        if len(self.issues) > 0:
            return "WARNINGS_PRESENT"
        
        return "VALIDATED_OK"


class ResponseValidator:
    """Main validation agent"""
    
    def __init__(self):
        # Type aliases mapping (same as in inventory_types.py)
        self.type_aliases = {
            "apim": ["APIM", "SAP_IS_APIM", "AZURE_APIM"],
            "sap": ["SAP_ODATA", "SAP_SOAP", "SAP_IDOC", "SAP_IS_APIM", "SAP_PO"],
            "azure": ["AZURE_APIM", "AZURE_FUNCTION"],
            "mule": ["MULE", "MULESOFT"],
            "rest": ["REST", "APIM", "SAP_IS_APIM"],
            "soap": ["SOAP", "SAP_SOAP"],
            "odata": ["ODATA", "SAP_ODATA"],
            "idoc": ["SAP_IDOC"]
        }
        
        # Keywords that indicate "all results"
        self.all_keywords = ["all", "complete", "full list", "every", "entire", "list all", "show all"]
        
        # Keywords that indicate type filtering
        self.type_keywords = list(self.type_aliases.keys())
    
    def validate_response(
        self,
        user_query: str,
        method_name: str,
        response_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Main validation entry point
        
        Args:
            user_query: Original user question
            method_name: Which method was used (vector_rag, db_lookup, etc.)
            response_data: Complete response with metadata
        
        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(method_name)
        
        # Run universal validations first
        self._validate_universal(user_query, response_data, result)
        
        # If universal checks fail critically, skip method-specific checks
        if result.confidence == 0.0:
            return result
        
        # Run method-specific validations
        if method_name == "db_lookup":
            self._validate_db_lookup(user_query, response_data, result)
        elif method_name == "vector_rag":
            self._validate_vector_rag(user_query, response_data, result)
        elif method_name == "graph_rag":
            self._validate_graph_rag(user_query, response_data, result)
        elif method_name == "llm_synthesis":
            self._validate_llm_synthesis(user_query, response_data, result)
        
        # Determine recommended action
        self._determine_recommended_action(result)
        
        return result
    
    def _validate_db_lookup(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate DuckDB query execution"""
        
        generated_query = response_data.get("generated_query", {})
        sql_query = response_data.get("sql_query", "")
        sql_params = response_data.get("sql_params", {})
        results = response_data.get("results", [])
        diagnostics = response_data.get("diagnostics", {})
        
        # ✅ Check 1: Type Filter Format
        if self._user_mentioned_type(user_query):
            type_filters = self._extract_type_filters(generated_query)
            
            for type_filter in type_filters:
                # RED FLAG: Numeric type ID
                filter_value = type_filter.get("eq") or type_filter.get("in", [None])[0]
                if filter_value and str(filter_value).isdigit():
                    issue = ValidationIssue(
                        severity="CRITICAL",
                        issue_type="ERR_OLD_TYPE_FILTER",
                        message=f"Type filter using numeric ID instead of string name",
                        expected="String type name (e.g., 'SAP_IS_APIM')",
                        actual=f"Numeric ID: {filter_value}",
                        fix="Restart Streamlit app - NLP processor module not reloaded",
                        confidence=0.0
                    )
                    result.add_issue(issue)
                    result.add_evidence(
                        "generated_query.where[].conditions[].field",
                        str(type_filter)
                    )
                    result.cross_validation_results["user_query_vs_generated_query"] = "FAIL"
                
                # RED FLAG: Using norm_type instead of type
                if type_filter.get("name") == "norm_type":
                    issue = ValidationIssue(
                        severity="CRITICAL",
                        issue_type="ERR_OLD_TYPE_FILTER",
                        message="Using deprecated 'norm_type' field instead of 'type'",
                        expected="Field name: 'type'",
                        actual="Field name: 'norm_type'",
                        fix="Restart Streamlit app - NLP processor using old code",
                        confidence=0.0
                    )
                    result.add_issue(issue)
                    result.add_evidence("generated_query", str(type_filter))
        
        # ✅ Check 2: LIMIT Clause Validation
        if self._user_wants_all_results(user_query):
            if "LIMIT 300" in sql_query or "LIMIT 300" in sql_query.upper():
                issue = ValidationIssue(
                    severity="CRITICAL",
                    issue_type="ERR_DEFAULT_LIMIT",
                    message="User asked for all results but SQL has default LIMIT 300",
                    expected="No LIMIT clause (to get complete results)",
                    actual="LIMIT 300 present in SQL",
                    fix="Restart Streamlit app - Translator module not reloaded",
                    confidence=0.0
                )
                result.add_issue(issue)
                result.add_evidence("sql_query", sql_query)
                result.cross_validation_results["generated_query_vs_sql"] = "FAIL"
        
        # ✅ Check 3: WHERE Clause Presence
        if self._user_specified_filter(user_query):
            if "WHERE" not in sql_query.upper():
                issue = ValidationIssue(
                    severity="HIGH",
                    issue_type="ERR_MISSING_WHERE",
                    message="User specified filter but SQL has no WHERE clause",
                    expected="WHERE clause with type/name/description filter",
                    actual="No WHERE clause in SQL",
                    fix="Check translator logic - filter not applied",
                    confidence=0.2
                )
                result.add_issue(issue)
                result.add_evidence("sql_query", sql_query)
                result.cross_validation_results["generated_query_vs_sql"] = "FAIL"
        
        # ✅ Check 4: Parameter Binding
        if "WHERE" in sql_query.upper() and "?" in sql_query:
            if not sql_params or sql_params == {}:
                issue = ValidationIssue(
                    severity="HIGH",
                    issue_type="ERR_MISSING_PARAMETERS",
                    message="WHERE clause has placeholders but no parameters bound",
                    expected="Parameters like {param_0_0: 'SAP_IS_APIM', ...}",
                    actual="Empty parameters: {}",
                    fix="Check translator parameter binding logic",
                    confidence=0.1
                )
                result.add_issue(issue)
                result.add_evidence("sql_params", str(sql_params))
                result.cross_validation_results["sql_vs_parameters"] = "FAIL"
        
        # ✅ Check 5: Result Count Cross-Validation
        if diagnostics and "type_distribution" in diagnostics:
            expected_count = self._get_expected_count(user_query, diagnostics)
            actual_count = len(results)
            
            if expected_count and abs(expected_count - actual_count) > 10:
                severity = "MEDIUM" if abs(expected_count - actual_count) < 50 else "HIGH"
                issue = ValidationIssue(
                    severity=severity,
                    issue_type="ERR_COUNT_MISMATCH",
                    message=f"Result count doesn't match expected from diagnostics",
                    expected=f"~{expected_count} records (from type distribution)",
                    actual=f"{actual_count} records returned",
                    fix="Check if type filter applied correctly",
                    confidence=0.3 if severity == "MEDIUM" else 0.2
                )
                result.add_issue(issue)
                result.diagnostic_summary["expected_result_count"] = expected_count
                result.diagnostic_summary["actual_result_count"] = actual_count
                result.cross_validation_results["results_vs_diagnostics"] = "FAIL"
        
        # ✅ Check 6: Type Distribution Validation
        if self._user_mentioned_type(user_query) and results:
            expected_types = self._get_expected_types(user_query)
            actual_types = self._extract_result_types(results)
            unexpected_types = set(actual_types) - set(expected_types)
            
            # Also check for numeric type values
            numeric_types = [t for t in actual_types if str(t).isdigit()]
            
            if numeric_types:
                issue = ValidationIssue(
                    severity="CRITICAL",
                    issue_type="ERR_NUMERIC_TYPES_IN_RESULTS",
                    message="Results contain numeric type values instead of type names",
                    expected=f"Type names: {expected_types}",
                    actual=f"Numeric types: {numeric_types}",
                    fix="Database has numeric types - check data ingestion",
                    confidence=0.0
                )
                result.add_issue(issue)
                result.diagnostic_summary["numeric_types_found"] = numeric_types
            
            if unexpected_types and not numeric_types:
                issue = ValidationIssue(
                    severity="HIGH",
                    issue_type="ERR_TYPE_DISTRIBUTION",
                    message="Results contain unexpected interface types",
                    expected=f"Only types: {expected_types}",
                    actual=f"Found unexpected: {list(unexpected_types)}",
                    fix="Check type filter logic or type alias expansion",
                    confidence=0.2
                )
                result.add_issue(issue)
                result.diagnostic_summary["expected_types"] = expected_types
                result.diagnostic_summary["actual_types"] = list(actual_types)
                result.cross_validation_results["results_vs_user_intent"] = "FAIL"
    
    def _validate_vector_rag(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate Vector RAG response"""
        
        chunks = response_data.get("chunks", [])
        
        # ✅ Check 1: Chunk Relevance
        low_similarity_count = 0
        for idx, chunk in enumerate(chunks[:5]):  # Check first 5 chunks
            similarity = chunk.get("similarity", chunk.get("score", 0))
            if similarity < 0.3:  # Low similarity threshold
                low_similarity_count += 1
        
        if low_similarity_count > 3:  # More than half of top 5 are low quality
            issue = ValidationIssue(
                severity="MEDIUM",
                issue_type="WARN_LOW_SIMILARITY",
                message=f"{low_similarity_count} of top 5 chunks have low similarity (<0.3)",
                fix="Query may be too specific or vector embeddings need retraining",
                confidence=0.5
            )
            result.add_issue(issue)
        
        # ✅ Check 2: Result Count
        if len(chunks) == 0:
            issue = ValidationIssue(
                severity="HIGH",
                issue_type="ERR_NO_CHUNKS",
                message="No relevant chunks found in vector store",
                fix="Query may be too specific, or vector store is empty/not indexed",
                confidence=0.3
            )
            result.add_issue(issue)
    
    def _validate_graph_rag(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate Graph RAG response"""
        
        seeds = response_data.get("seeds", [])
        neighborhood = response_data.get("neighborhood", [])
        
        # ✅ Check 1: Seed Extraction
        if not seeds:
            issue = ValidationIssue(
                severity="MEDIUM",
                issue_type="WARN_NO_SEEDS",
                message="No seed entities extracted from query",
                fix="Check seed extraction logic or rephrase query with specific entity names",
                confidence=0.5
            )
            result.add_issue(issue)
        
        # ✅ Check 2: Neighborhood Size
        if len(neighborhood) == 0 and seeds:
            issue = ValidationIssue(
                severity="HIGH",
                issue_type="ERR_EMPTY_NEIGHBORHOOD",
                message=f"Seeds found ({seeds}) but no neighborhood returned",
                fix="Check Neo4j connection, graph data, or relationship structure",
                confidence=0.3
            )
            result.add_issue(issue)
    
    def _validate_llm_synthesis(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate LLM Synthesis response"""
        
        prompt = response_data.get("prompt", "")
        context = response_data.get("context", [])
        llm_response = response_data.get("llm_response", "")
        
        # ✅ Check 1: Prompt Quality
        if len(prompt) < 100:
            issue = ValidationIssue(
                severity="MEDIUM",
                issue_type="WARN_SHORT_PROMPT",
                message=f"Synthesis prompt very short ({len(prompt)} chars)",
                fix="Check prompt builder - may lack sufficient context",
                confidence=0.6
            )
            result.add_issue(issue)
        
        # ✅ Check 2: Context Completeness
        if not context:
            issue = ValidationIssue(
                severity="HIGH",
                issue_type="ERR_NO_CONTEXT",
                message="No context provided to LLM for synthesis",
                fix="Check context gathering from other methods (vector_rag, graph_rag)",
                confidence=0.3
            )
            result.add_issue(issue)
        
        # ✅ Check 3: Hallucination Detection
        if self._detect_hallucination_markers(llm_response):
            issue = ValidationIssue(
                severity="MEDIUM",
                issue_type="WARN_POSSIBLE_HALLUCINATION",
                message="LLM response contains uncertainty markers",
                fix="Verify response against source data; may need more context",
                confidence=0.5
            )
            result.add_issue(issue)
    
    def _validate_universal(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Universal validations that apply to all methods"""
        
        # ✅ Check 1: Response Not Empty
        if not response_data:
            issue = ValidationIssue(
                severity="CRITICAL",
                issue_type="ERR_EMPTY_RESPONSE",
                message="Response data is empty or null",
                fix="Check method execution - may have failed silently",
                confidence=0.0
            )
            result.add_issue(issue)
            return
        
        # ✅ Check 2: Error in Response
        if "error" in response_data and response_data["error"]:
            issue = ValidationIssue(
                severity="CRITICAL",
                issue_type="ERR_EXECUTION_ERROR",
                message=f"Execution error: {response_data['error']}",
                fix="Check logs and stack trace for details",
                confidence=0.0
            )
            result.add_issue(issue)
        
        # ✅ Check 3: Timeout Warning
        execution_time = response_data.get("execution_time", 0)
        if execution_time > 30:  # 30 seconds
            issue = ValidationIssue(
                severity="MEDIUM",
                issue_type="WARN_SLOW_RESPONSE",
                message=f"Query took {execution_time:.1f}s (>30s threshold)",
                fix="Consider optimization, indexing, or caching",
                confidence=0.8
            )
            result.add_issue(issue)
    
    def _determine_recommended_action(self, result: ValidationResult):
        """Determine what action should be taken based on issues"""
        
        error_types = [issue.issue_type for issue in result.issues]
        
        # Check for module reload issues
        module_reload_errors = ["ERR_OLD_TYPE_FILTER", "ERR_DEFAULT_LIMIT"]
        if any(err in error_types for err in module_reload_errors):
            result.recommended_action = "RESTART_APPLICATION"
            result.diagnostic_summary["modules_not_reloaded"] = [
                "src.nlp_processor",
                "duckdb_engine.translator"
            ]
            return
        
        # Check for configuration issues
        if "ERR_NO_CONTEXT" in error_types or "ERR_EMPTY_RESPONSE" in error_types:
            result.recommended_action = "CHECK_CONFIGURATION"
            return
        
        # Check for data issues
        if "ERR_NUMERIC_TYPES_IN_RESULTS" in error_types:
            result.recommended_action = "REINGEST_DATA"
            return
        
        # Check for query reformulation
        if "WARN_NO_SEEDS" in error_types or "ERR_NO_CHUNKS" in error_types:
            result.recommended_action = "REFORMULATE_QUERY"
            return
        
        # Otherwise, just review
        if len(result.issues) > 0:
            result.recommended_action = "REVIEW_ISSUES"
        else:
            result.recommended_action = "NONE"
    
    # ==================== Helper Methods ====================
    
    def _user_mentioned_type(self, query: str) -> bool:
        """Check if user mentioned interface type"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.type_keywords)
    
    def _user_wants_all_results(self, query: str) -> bool:
        """Check if user wants complete result set"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.all_keywords)
    
    def _user_specified_filter(self, query: str) -> bool:
        """Check if user specified any filter"""
        filter_indicators = [
            "where", "with", "type", "name", "sender", "receiver",
            "status", "contains", "like", "equal", "is"
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in filter_indicators)
    
    def _extract_type_filters(self, generated_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract type filter conditions from generated query"""
        type_filters = []
        query_dict = generated_query.get("query", generated_query)
        where_clauses = query_dict.get("where", [])
        
        for where_group in where_clauses:
            for condition in where_group.get("conditions", []):
                field = condition.get("field", {})
                field_name = field.get("name", "")
                if "type" in field_name.lower():  # Catches type, norm_type, etc.
                    type_filters.append(field)
        
        return type_filters
    
    def _get_expected_count(self, user_query: str, diagnostics: Dict[str, Any]) -> Optional[int]:
        """Get expected result count from diagnostics"""
        type_dist = diagnostics.get("type_distribution", {})
        query_lower = user_query.lower()
        
        # Map user query to expected types and sum their counts
        for alias, types in self.type_aliases.items():
            if alias in query_lower:
                total = sum(type_dist.get(t, 0) for t in types)
                if total > 0:
                    return total
        
        return None
    
    def _get_expected_types(self, user_query: str) -> List[str]:
        """Get list of expected types based on user query"""
        query_lower = user_query.lower()
        
        for alias, types in self.type_aliases.items():
            if alias in query_lower:
                return types
        
        return []
    
    def _extract_result_types(self, results: List[Dict[str, Any]]) -> Set[str]:
        """Extract unique types from result set"""
        types = set()
        for record in results:
            if "type" in record and record["type"]:
                types.add(str(record["type"]))
        return types
    
    def _detect_hallucination_markers(self, text: str) -> bool:
        """Detect common LLM hallucination markers"""
        if not text:
            return False
        
        markers = [
            "i don't have access to",
            "i cannot see",
            "i'm not sure",
            "i cannot verify",
            "may or may not",
            "possibly",
            "might be",
            "i don't know"
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in markers)


# Convenience function for quick validation
def validate_response(
    user_query: str,
    method_name: str,
    response_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick validation function
    
    Returns:
        Dict with validation results
    """
    validator = ResponseValidator()
    result = validator.validate_response(user_query, method_name, response_data)
    return result.to_dict()


__all__ = [
    "ResponseValidator",
    "ValidationResult",
    "ValidationIssue",
    "validate_response"
]


