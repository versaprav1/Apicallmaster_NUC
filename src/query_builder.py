from typing import Dict, List, Any, Optional, Union

class QueryBuilder:
    """Advanced query builder for WHINT Integration Cockpit API"""
    
    def __init__(self):
        self.supported_entities = [
            "inventory", "task", "datasource", "dataFlow", 
            "system", "logEntry", "runs", "properties", 
            "metadata", "tags", "objects", "sender", "receiver"
        ]
        self.supported_operators = ["eq", "ne", "like", "gt", "lt", "gte", "lte", "in"]
    
    def create_simple_query(
        self, 
        entity: str, 
        fields: Optional[List[str]] = None,
        filter_field: Optional[str] = None,
        filter_operator: Optional[str] = "eq",
        filter_value: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Create a simple query with basic filtering following WHINT API structure"""
        
        if entity not in self.supported_entities:
            raise ValueError(f"Unsupported entity: {entity}")
        
        query = {
            "query": {
                "entity": entity,
                "limit": limit,
                "offset": offset
            }
        }
        
        # Add fields if specified (empty list means all fields in WHINT API)
        if fields:
            query["query"]["fields"] = fields
        else:
            query["query"]["fields"] = []
        
        # Add filter if specified - following WHINT API where structure
        if filter_field and filter_value:
            if filter_operator not in self.supported_operators:
                raise ValueError(f"Unsupported operator: {filter_operator}")
            
            query["query"]["where"] = [{
                "option": 0,  # 0 = AND, 1 = OR
                "conditions": [{
                    "field": {
                        "name": filter_field,
                        filter_operator: filter_value
                    }
                }]
            }]
        
        return query
    
    def create_advanced_query(
        self,
        entity: str,
        fields: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
        offset: int = 0,
        logic_operator: str = "AND"
    ) -> Dict[str, Any]:
        """Create an advanced query with complex filtering and joins"""
        
        if entity not in self.supported_entities:
            raise ValueError(f"Unsupported entity: {entity}")
        
        query = {
            "query": {
                "entity": entity,
                "limit": limit,
                "offset": offset
            }
        }
        
        # Add fields
        if fields:
            query["query"]["fields"] = fields
        
        # Add filters
        if filters:
            where_conditions = []
            for filter_item in filters:
                field_name = filter_item.get("field")
                operator = filter_item.get("operator", "eq")
                value = filter_item.get("value")
                not_condition = filter_item.get("not", False)
                
                if field_name and value:
                    condition = {
                        "field": {
                            "name": field_name,
                            operator: value
                        }
                    }
                    
                    if not_condition:
                        condition["not"] = True
                    
                    where_conditions.append(condition)
            
            if where_conditions:
                query["query"]["where"] = [{
                    "option": 0 if logic_operator == "AND" else 1,
                    "conditions": where_conditions
                }]
        
        # Add joins
        if joins:
            with_clauses = []
            for join in joins:
                join_entity = join.get("entity")
                join_fields = join.get("fields", [])
                join_filters = join.get("filters", [])
                
                if join_entity:
                    with_clause = {
                        "entity": join_entity
                    }
                    
                    if join_fields:
                        with_clause["fields"] = join_fields
                    
                    # Add nested filters for joined entities
                    if join_filters:
                        join_conditions = []
                        for filter_item in join_filters:
                            field_name = filter_item.get("field")
                            operator = filter_item.get("operator", "eq")
                            value = filter_item.get("value")
                            
                            if field_name and value:
                                join_conditions.append({
                                    "field": {
                                        "name": field_name,
                                        operator: value
                                    }
                                })
                        
                        if join_conditions:
                            with_clause["where"] = [{
                                "option": 0,
                                "conditions": join_conditions
                            }]
                    
                    with_clauses.append(with_clause)
            
            if with_clauses:
                query["query"]["with"] = with_clauses
        
        return query
    
    def create_entity_filter_query(
        self,
        entity: str,
        fields: Optional[List[str]] = None,
        entity_filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Create a query with entity-based filtering (complex nested conditions)"""
        
        query = {
            "query": {
                "entity": entity,
                "limit": limit,
                "offset": offset
            }
        }
        
        if fields:
            query["query"]["fields"] = fields
        
        if entity_filters:
            where_conditions = []
            
            for entity_filter in entity_filters:
                filter_entity = entity_filter.get("entity")
                predicates = entity_filter.get("predicates", [])
                logic_op = entity_filter.get("logic", "AND")
                
                if filter_entity and predicates:
                    entity_condition = {
                        "entity": {
                            "name": filter_entity,
                            "predicates": []
                        }
                    }
                    
                    for predicate in predicates:
                        conditions = predicate.get("conditions", [])
                        if conditions:
                            predicate_obj = {
                                "option": 0 if logic_op == "AND" else 1,
                                "conditions": []
                            }
                            
                            for condition in conditions:
                                field_name = condition.get("field")
                                operator = condition.get("operator", "eq")
                                value = condition.get("value")
                                
                                if field_name and value:
                                    predicate_obj["conditions"].append({
                                        "field": {
                                            "name": field_name,
                                            operator: value
                                        }
                                    })
                            
                            if predicate_obj["conditions"]:
                                entity_condition["entity"]["predicates"].append(predicate_obj)
                    
                    if entity_condition["entity"]["predicates"]:
                        where_conditions.append(entity_condition)
            
            if where_conditions:
                query["query"]["where"] = [{
                    "option": 1,  # OR between different entity filters
                    "conditions": where_conditions
                }]
        
        return query
    
    def create_inventory_with_relationships_query(
        self,
        fields: Optional[List[str]] = None,
        inventory_type: Optional[int] = None,
        include_properties: bool = True,
        include_metadata: bool = True,
        include_tags: bool = True,
        include_sender: bool = True,
        include_receiver: bool = True,
        limit: int = 5000,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Create a comprehensive inventory query with all relationships - based on WHINT API examples"""
        
        query = {
            "query": {
                "entity": "inventory",
                "fields": fields or ["name", "description", "type", "sender_name", "receiver_name"],
                "limit": limit,
                "offset": offset
            }
        }
        
        # Add type filter if specified
        if inventory_type is not None:
            query["query"]["where"] = [{
                "option": 0,
                "conditions": [{
                    "field": {
                        "name": "type",
                        "eq": str(inventory_type)
                    }
                }]
            }]
        
        # Build with clauses based on WHINT API documentation examples
        with_clauses = []
        
        if include_sender:
            with_clauses.append({
                "entity": "sender",
                "fields": ["name"],
                "with": [{
                    "entity": "properties",
                    "fields": ["type_id", "value"],
                    "with": [{
                        "entity": "type",
                        "fields": ["name", "kind"]
                    }]
                }]
            })
        
        if include_receiver:
            with_clauses.append({
                "entity": "receiver", 
                "fields": ["name"],
                "with": [{
                    "entity": "properties",
                    "fields": ["type_id", "value"],
                    "with": [{
                        "entity": "type",
                        "fields": ["name", "kind"]
                    }]
                }]
            })
        
        if include_tags:
            with_clauses.append({
                "entity": "tags",
                "fields": ["value", "tag_id"],
                "with": [{
                    "entity": "tag",
                    "fields": ["name"]
                }]
            })
        
        if include_properties:
            with_clauses.append({
                "entity": "properties",
                "fields": ["type_id", "value"],
                "with": [{
                    "entity": "type",
                    "fields": ["name", "kind"]
                }]
            })
        
        if include_metadata:
            with_clauses.append({
                "entity": "metadata",
                "fields": ["name", "value"]
            })
        
        if with_clauses:
            query["query"]["with"] = with_clauses
        
        return query
    
    def create_whint_example_query(
        self,
        query_type: str = "basic_inventory",
        **kwargs
    ) -> Dict[str, Any]:
        """Create queries based on WHINT API documentation examples"""
        
        if query_type == "basic_inventory":
            # Basic inventory query with all relationships
            return {
                "query": {
                    "entity": "inventory",
                    "fields": ["name", "description"],
                    "with": [
                        {
                            "entity": "sender",
                            "fields": ["name"],
                            "with": [
                                {
                                    "entity": "properties",
                                    "fields": ["type_id", "value"],
                                    "with": [{
                                        "entity": "type",
                                        "fields": ["name", "kind"]
                                    }]
                                }
                            ]
                        },
                        {
                            "entity": "receiver",
                            "fields": ["name"],
                            "with": [
                                {
                                    "entity": "properties",
                                    "fields": ["type_id", "value"],
                                    "with": [{
                                        "entity": "type",
                                        "fields": ["name", "kind"]
                                    }]
                                }
                            ]
                        },
                        {
                            "entity": "tags",
                            "fields": ["value", "tag_id"],
                            "with": [{
                                "entity": "tag",
                                "fields": ["name"]
                            }]
                        },
                        {
                            "entity": "properties",
                            "fields": ["type_id", "value"],
                            "with": [{
                                "entity": "type",
                                "fields": ["name", "kind"]
                            }]
                        },
                        {
                            "entity": "metadata",
                            "fields": ["name", "value"]
                        }
                    ],
                    "limit": kwargs.get("limit", 5000),
                    "offset": kwargs.get("offset", 0)
                }
            }
        
        elif query_type == "inventory_by_name":
            # Query inventory by name with LIKE operator
            search_term = kwargs.get("search_term", "Connect")
            return {
                "query": {
                    "entity": "inventory",
                    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
                    "where": [{
                        "option": 1,
                        "conditions": [
                            {
                                "field": {
                                    "name": "name",
                                    "like": search_term
                                }
                            }
                        ]
                    }],
                    "limit": kwargs.get("limit", 300),
                    "offset": kwargs.get("offset", 0)
                }
            }
        
        elif query_type == "inventory_with_metadata":
            # Query inventory with properties and metadata
            return {
                "query": {
                    "entity": "inventory",
                    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
                    "with": [
                        {
                            "entity": "metadata",
                            "fields": ["name", "value"]
                        },
                        {
                            "entity": "properties",
                            "fields": ["type_id", "value"]
                        }
                    ]
                }
            }
        
        elif query_type == "failed_tasks":
            # Query tasks with failed runs
            return {
                "query": {
                    "entity": "task",
                    "fields": [],
                    "with": [
                        {
                            "entity": "runs",
                            "where": [{
                                "option": 1,
                                "conditions": [
                                    {
                                        "field": {
                                            "name": "successful",
                                            "eq": "false"
                                        }
                                    }
                                ]
                            }]
                        }
                    ]
                }
            }
        
        elif query_type == "complex_entity_filter":
            # Complex query with entity filtering (from documentation example)
            data_source_id = kwargs.get("data_source_id", "djtSuXNusGA")
            return {
                "query": {
                    "entity": "inventory",
                    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
                    "where": [{
                        "conditions": [
                            {
                                "entity": {
                                    "name": "sender",
                                    "predicates": [{
                                        "conditions": [{
                                            "field": {
                                                "name": "data_source_id",
                                                "like": data_source_id
                                            }
                                        }]
                                    }]
                                }
                            },
                            {
                                "entity": {
                                    "name": "receiver",
                                    "predicates": [{
                                        "conditions": [{
                                            "field": {
                                                "name": "data_source_id",
                                                "like": data_source_id
                                            }
                                        }]
                                    }]
                                }
                            },
                            {
                                "not": True,
                                "field": {
                                    "name": "type",
                                    "eq": "21"
                                }
                            },
                            {
                                "not": True,
                                "field": {
                                    "name": "type",
                                    "eq": "13"
                                }
                            }
                        ]
                    }],
                    "with": [
                        {
                            "entity": "dataSource",
                            "fields": ["name"]
                        },
                        {
                            "entity": "sender",
                            "with": [
                                {
                                    "entity": "dataSource",
                                    "fields": ["name"]
                                }
                            ]
                        },
                        {
                            "entity": "receiver",
                            "with": [
                                {
                                    "entity": "dataSource",
                                    "fields": ["name"]
                                }
                            ]
                        },
                        {
                            "entity": "metadata",
                            "fields": ["name", "value"]
                        },
                        {
                            "entity": "properties",
                            "fields": ["type_id", "value"]
                        },
                        {
                            "entity": "objects",
                            "fields": ["id", "name", "description"]
                        },
                        {
                            "entity": "tags"
                        }
                    ]
                }
            }
        
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def create_upsert_query(self, entity: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an upsert query for write operations"""
        
        if entity not in self.supported_entities:
            raise ValueError(f"Unsupported entity: {entity}")
        
        if not items:
            raise ValueError("Items list cannot be empty")
        
        return {
            "upsert": {
                entity: items
            }
        }
    
    def create_log_query(
        self,
        level: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        message_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Create a query for log entries with time and level filtering"""
        
        query = {
            "query": {
                "entity": "logEntry",
                "fields": ["id", "create_time", "change_time", "level", "message"],
                "limit": limit,
                "offset": offset
            }
        }
        
        conditions = []
        
        if level is not None:
            conditions.append({
                "field": {
                    "name": "level",
                    "eq": str(level)
                }
            })
        
        if start_time:
            conditions.append({
                "field": {
                    "name": "create_time",
                    "gte": start_time
                }
            })
        
        if end_time:
            conditions.append({
                "field": {
                    "name": "create_time",
                    "lte": end_time
                }
            })
        
        if message_filter:
            conditions.append({
                "field": {
                    "name": "message",
                    "like": message_filter
                }
            })
        
        if conditions:
            query["query"]["where"] = [{
                "option": 0,  # AND all conditions
                "conditions": conditions
            }]
        
        return query
    
    def create_task_with_runs_query(
        self,
        successful_only: Optional[bool] = None,
        data_source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Create a query for tasks with their runs"""
        
        query = {
            "query": {
                "entity": "task",
                "fields": ["id", "create_time", "change_time", "start_date", "data_source_id", "type"],
                "limit": limit,
                "offset": offset,
                "with": [{
                    "entity": "runs",
                    "fields": ["id", "create_time", "start_time", "end_time", "duration", "successful"]
                }]
            }
        }
        
        # Add task-level filters
        conditions = []
        if data_source_id:
            conditions.append({
                "field": {
                    "name": "data_source_id",
                    "eq": data_source_id
                }
            })
        
        if conditions:
            query["query"]["where"] = [{
                "option": 0,
                "conditions": conditions
            }]
        
        # Add run-level filters
        if successful_only is not None:
            run_conditions = [{
                "field": {
                    "name": "successful",
                    "eq": "true" if successful_only else "false"
                }
            }]
            
            query["query"]["with"][0]["where"] = [{
                "option": 0,
                "conditions": run_conditions
            }]
        
        return query
    
    def validate_query(self, query: Dict[str, Any]) -> List[str]:
        """Validate a query and return list of errors"""
        errors = []
        
        if "query" not in query and "upsert" not in query:
            errors.append("Query must contain either 'query' or 'upsert' key")
            return errors
        
        if "query" in query:
            query_obj = query["query"]
            
            # Validate entity
            entity = query_obj.get("entity")
            if not entity:
                errors.append("Entity is required")
            elif entity not in self.supported_entities:
                errors.append(f"Unsupported entity: {entity}")
            
            # Validate limit and offset
            limit = query_obj.get("limit", 100)
            offset = query_obj.get("offset", 0)
            
            if not isinstance(limit, int) or limit <= 0:
                errors.append("Limit must be a positive integer")
            if not isinstance(offset, int) or offset < 0:
                errors.append("Offset must be a non-negative integer")
            
            # Validate where clauses
            if "where" in query_obj:
                for where_clause in query_obj["where"]:
                    if "conditions" not in where_clause:
                        errors.append("Where clause must contain 'conditions'")
        
        return errors
