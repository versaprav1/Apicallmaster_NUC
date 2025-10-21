"""
DuckDB Query Translator

Converts WHINT Integration Cockpit JSON queries to SQL for execution against DuckDB.
Handles entity mapping, field selection, WHERE conditions, WITH clauses, and pagination.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from src.inventory_types import INVENTORY_TYPES, INVENTORY_TYPES_BY_NAME


class DuckDBTranslator:
    """Translates WHINT JSON queries to DuckDB SQL."""
    
    def __init__(self):
        # Entity to table/view mapping
        self.entity_mapping = {
            'inventory': 'inventory_view',
            'task': 'raw_all',  # TODO: Create task_view when we have task data
            'logEntry': 'raw_all',  # TODO: Create log_view when we have log data
            'datasource': 'raw_all',  # TODO: Create datasource_view when we have datasource data
            'system': 'raw_all',  # TODO: Create system_view when we have system data
            'dataFlow': 'raw_all',  # TODO: Create dataflow_view when we have dataflow data
        }
        
        # Field mapping for inventory_view
        self.field_mapping = {
            'inventory': {
                'id': 'norm_name',  # Use name as ID since we don't have actual IDs
                'name': 'norm_name',
                'type': 'norm_type',
                'description': 'norm_description',
                'sender_name': 'norm_sender_name',
                'receiver_name': 'norm_receiver_name',
                'metadata': 'metadata',
                'properties': 'properties',
                'tags': 'tags',
                'sender': 'sender',
                'receiver': 'receiver',
            }
        }
        
        # SQL operator mapping
        self.operator_mapping = {
            'eq': '=',
            'ne': '!=',
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
            'like': 'ILIKE',
            'in': 'IN',
            'not_in': 'NOT IN',
        }

    def translate(self, whint_query: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Translate WHINT JSON query to SQL.
        
        Args:
            whint_query: WHINT API query structure
            
        Returns:
            Tuple of (SQL query, parameters dict)
        """
        query_part = whint_query.get('query', {})
        entity = query_part.get('entity', 'inventory')
        
        # Get base table/view
        base_table = self.entity_mapping.get(entity, 'inventory_view')
        
        # Build SELECT clause
        select_clause = self._build_select(query_part, entity)
        
        # Build FROM clause
        from_clause = f"FROM {base_table}"
        
        # Build WHERE clause
        where_clause, params = self._build_where(query_part, entity)
        
        # Build WITH clause (joins for related entities)
        join_clause = self._build_with(query_part, entity)
        
        # Build ORDER BY (default by name for consistency)
        order_clause = "ORDER BY norm_name"
        
        # Build LIMIT/OFFSET
        limit_clause = self._build_limit_offset(query_part)
        
        # Combine SQL
        sql_parts = [select_clause, from_clause]
        if join_clause:
            sql_parts.append(join_clause)
        if where_clause:
            sql_parts.append(where_clause)
        sql_parts.extend([order_clause, limit_clause])
        
        sql = " ".join(sql_parts)
        
        return sql, params

    def _build_select(self, query_part: Dict[str, Any], entity: str) -> str:
        """Build SELECT clause from fields specification."""
        fields = query_part.get('fields', [])
        
        if not fields:
            # Default fields based on entity
            if entity == 'inventory':
                return "SELECT norm_name, norm_type, norm_description, norm_sender_name, norm_receiver_name, metadata, properties, tags"
            else:
                return "SELECT *"
        
        # Map WHINT fields to SQL columns
        field_mapping = self.field_mapping.get(entity, {})
        sql_fields = []
        
        for field in fields:
            sql_field = field_mapping.get(field, field)
            sql_fields.append(sql_field)
        
        return f"SELECT {', '.join(sql_fields)}"

    def _build_where(self, query_part: Dict[str, Any], entity: str) -> Tuple[str, Dict[str, Any]]:
        """Build WHERE clause from conditions."""
        where_conditions = query_part.get('where', [])
        if not where_conditions:
            return "", {}
        
        params = {}
        param_counter = 0
        sql_conditions = []
        
        for where_group in where_conditions:
            group_conditions = []
            option = where_group.get('option', 1)  # 1 = AND, 2 = OR
            
            conditions = where_group.get('conditions', [])
            for condition in conditions:
                sql_condition, condition_params = self._translate_condition(condition, entity, param_counter)
                if sql_condition:
                    group_conditions.append(sql_condition)
                    params.update(condition_params)
                    param_counter += len(condition_params)
            
            if group_conditions:
                if option == 2:  # OR
                    group_sql = f"({' OR '.join(group_conditions)})"
                else:  # AND
                    group_sql = f"({' AND '.join(group_conditions)})"
                sql_conditions.append(group_sql)
        
        if sql_conditions:
            where_clause = f"WHERE {' AND '.join(sql_conditions)}"
            return where_clause, params
        
        return "", {}

    def _translate_condition(self, condition: Dict[str, Any], entity: str, param_start: int) -> Tuple[str, Dict[str, Any]]:
        """Translate a single condition to SQL."""
        params = {}
        param_counter = param_start
        
        # Handle field conditions
        if 'field' in condition:
            field_condition = condition['field']
            field_name = field_condition.get('name')
            operator = field_condition.get('operator', 'eq')
            
            # Map field name to SQL column
            field_mapping = self.field_mapping.get(entity, {})
            sql_field = field_mapping.get(field_name, field_name)
            
            # Handle special field types
            if field_name == 'type':
                sql_field, value = self._resolve_inventory_type_filter(field_condition)
                if sql_field and value is not None:
                    param_name = f"param_{param_counter}"
                    params[param_name] = value
                    sql_operator = self.operator_mapping.get(operator, '=')
                    return f"{sql_field} {sql_operator} :{param_name}", params
            else:
                # Regular field condition
                value = field_condition.get('value')
                if value is not None:
                    param_name = f"param_{param_counter}"
                    params[param_name] = value
                    sql_operator = self.operator_mapping.get(operator, '=')
                    
                    # Handle LIKE with wildcards
                    if operator == 'like' and isinstance(value, str):
                        params[param_name] = f"%{value}%"
                    
                    return f"{sql_field} {sql_operator} :{param_name}", params
        
        # Handle entity conditions (nested predicates)
        elif 'entity' in condition:
            entity_condition = condition['entity']
            entity_name = entity_condition.get('name')
            predicates = entity_condition.get('predicates', [])
            
            # For now, handle simple sender/receiver conditions
            if entity_name in ['sender', 'receiver']:
                for predicate in predicates:
                    for pred_condition in predicate.get('conditions', []):
                        if 'field' in pred_condition:
                            field_condition = pred_condition['field']
                            field_name = field_condition.get('name')
                            value = field_condition.get('value')
                            
                            if field_name == 'data_source_id' and value:
                                param_name = f"param_{param_counter}"
                                params[param_name] = value
                                return f"{entity_name}->>'data_source_id' = :{param_name}", params
        
        # Handle NOT conditions
        elif 'not' in condition and condition['not']:
            inner_condition = {k: v for k, v in condition.items() if k != 'not'}
            inner_sql, inner_params = self._translate_condition(inner_condition, entity, param_counter)
            if inner_sql:
                return f"NOT ({inner_sql})", inner_params
        
        return "", {}

    def _resolve_inventory_type_filter(self, field_condition: Dict[str, Any]) -> Tuple[str, Any]:
        """Resolve inventory type filter to numeric IDs."""
        operator = field_condition.get('operator', 'eq')
        value = field_condition.get('value')
        
        if operator == 'eq':
            # Single type
            if isinstance(value, str):
                # String label to numeric ID
                type_id = INVENTORY_TYPES.get(value.lower())
                if type_id is not None:
                    return "CAST(norm_type AS INTEGER)", type_id
            elif isinstance(value, (int, str)) and str(value).isdigit():
                # Already numeric
                return "CAST(norm_type AS INTEGER)", int(value)
        elif operator == 'in':
            # Multiple types
            if isinstance(value, list):
                resolved_ids = []
                for v in value:
                    if isinstance(v, str):
                        type_id = INVENTORY_TYPES.get(v.lower())
                        if type_id is not None:
                            resolved_ids.append(type_id)
                    elif isinstance(v, (int, str)) and str(v).isdigit():
                        resolved_ids.append(int(v))
                
                if resolved_ids:
                    return "CAST(norm_type AS INTEGER)", resolved_ids
        
        # Fallback: use string comparison
        return "norm_type", value

    def _build_with(self, query_part: Dict[str, Any], entity: str) -> str:
        """Build WITH clause (joins for related entities)."""
        with_clauses = query_part.get('with', [])
        if not with_clauses:
            return ""
        
        joins = []
        for with_clause in with_clauses:
            with_entity = with_clause.get('entity')
            with_fields = with_clause.get('fields', [])
            
            # For inventory, metadata/properties/tags are already in the main table
            if entity == 'inventory' and with_entity in ['metadata', 'properties', 'tags']:
                # These are already selected in the main query, no join needed
                continue
            
            # TODO: Implement proper joins for other entities
            # For now, just note that we're including these fields
        
        return " ".join(joins) if joins else ""

    def _build_limit_offset(self, query_part: Dict[str, Any]) -> str:
        """Build LIMIT and OFFSET clause."""
        limit = query_part.get('limit', 300)  # Default limit
        offset = query_part.get('offset', 0)
        
        if limit and limit > 0:
            return f"LIMIT {limit} OFFSET {offset}"
        return ""

    def validate_query(self, whint_query: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate WHINT query structure."""
        if not isinstance(whint_query, dict):
            return False, "Query must be a dictionary"
        
        query_part = whint_query.get('query', {})
        if not isinstance(query_part, dict):
            return False, "Query must have a 'query' object"
        
        entity = query_part.get('entity')
        if not entity:
            return False, "Query must specify an entity"
        
        if entity not in self.entity_mapping:
            return False, f"Unsupported entity: {entity}"
        
        return True, "Valid query"


def translate_whint_to_sql(whint_query: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to translate WHINT query to SQL.
    
    Args:
        whint_query: WHINT API query structure
        
    Returns:
        Tuple of (SQL query, parameters dict)
    """
    translator = DuckDBTranslator()
    return translator.translate(whint_query)


if __name__ == "__main__":
    # Test the translator
    test_query = {
        "query": {
            "entity": "inventory",
            "fields": ["name", "type", "description"],
            "where": [{
                "option": 1,
                "conditions": [{
                    "field": {
                        "name": "type",
                        "eq": "1"
                    }
                }]
            }],
            "limit": 10
        }
    }
    
    translator = DuckDBTranslator()
    sql, params = translator.translate(test_query)
    print("SQL:", sql)
    print("Params:", params)
