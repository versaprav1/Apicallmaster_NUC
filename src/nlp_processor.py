import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
from src.query_builder import QueryBuilder
from src.inventory_types import INVENTORY_TYPES
from src.prompt_builder import build_system_prompt_translation

class NLPProcessor:
    """Natural Language Processing for WHINT API queries"""
    
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.query_builder = QueryBuilder()
        
        # Define common patterns and mappings
        self.entity_patterns = {
            r'\b(interface|integration|flow)s?\b': 'inventory',
            r'\btasks?\b': 'task',
            r'\b(data\s*source|datasource)s?\b': 'datasource',
            r'\b(data\s*flow|dataflow)s?\b': 'dataFlow',
            r'\bsystems?\b': 'system',
            r'\b(log|logs|log\s*entr(y|ies))\b': 'logEntry'
        }
        
        self.operator_patterns = {
            r'\b(equal|equals|is|are)\b': 'eq',
            r'\b(like|contains|includes?)\b': 'like',
            r'\b(greater\s*than|above|more\s*than)\b': 'gt',
            r'\b(less\s*than|below|fewer\s*than)\b': 'lt',
            r'\b(not|isn\'t|aren\'t)\b': 'ne'
        }
        
        self.common_fields = {
            'inventory': ['name', 'description', 'type', 'sender_name', 'receiver_name'],
            'task': ['name', 'start_date', 'data_source_id'],
            'datasource': ['name', 'type', 'category'],
            'system': ['name', 'description'],
            'logEntry': ['level', 'message', 'create_time']
        }
    
    def translate_to_api_query(self, natural_query: str) -> Optional[Dict[str, Any]]:
        """Translate natural language query to API query"""
        if not self.client:
            return self._rule_based_translation(natural_query)
        
        try:
            # Try LLM-based translation first
            llm_query = self._llm_based_translation(natural_query)
            if llm_query:
                return llm_query
        except Exception as e:
            print(f"LLM translation failed: {str(e)}")
        
        # Fallback to rule-based translation
        return self._rule_based_translation(natural_query)
    
    def analyze_query_intent(self, natural_query: str) -> Dict[str, Any]:
        """Analyze query to determine if it requires graph processing"""
        query_lower = natural_query.lower()
        
        # Graph-worthy patterns
        graph_patterns = [
            # Relationship patterns
            r'\b(?:which|what)\s+(?:systems?|interfaces?)\s+(?:send|sends|sending)\s+(?:to|data\s+to)\b',
            r'\b(?:which|what)\s+(?:systems?|interfaces?)\s+(?:receive|receives|receiving)\s+(?:from|data\s+from)\b',
            r'\b(?:systems?|interfaces?)\s+(?:that|which)\s+(?:send|sends|sending)\s+(?:to|data\s+to)\b',
            r'\b(?:systems?|interfaces?)\s+(?:that|which)\s+(?:receive|receives|receiving)\s+(?:from|data\s+from)\b',
            
            # Path/connection patterns
            r'\b(?:shortest\s+)?path\s+(?:from|between)\b',
            r'\b(?:route|routing|connection)\s+(?:from|between)\b',
            r'\b(?:how\s+does|how\s+do)\s+\w+\s+(?:connect|link|relate)\s+(?:to|with)\b',
            r'\b(?:connect|connected|connection|links?|linking)\s+(?:to|with|between)\b',
            
            # Neighborhood/related patterns
            r'\b(?:neighbors?|neighbourhood|related\s+to|associated\s+with)\b',
            r'\b(?:what\s+)?(?:systems?|interfaces?)\s+(?:are\s+)?(?:connected|linked|related)\s+(?:to|with)\b',
            r'\b(?:dependencies?|depends?\s+on|depends?\s+upon)\b',
            
            # Multi-hop patterns
            r'\b(?:through|via|passing\s+through)\b',
            r'\b(?:intermediate|middle|stepping\s+stone)\b',
            
            # Data flow patterns
            r'\b(?:data\s+flow|information\s+flow|message\s+flow)\b',
            r'\b(?:sender|source|origin)\s+(?:and|to)\s+(?:receiver|destination|target)\b',
        ]
        
        # Check for graph patterns
        requires_graph = any(re.search(pattern, query_lower) for pattern in graph_patterns)
        
        # Extract graph seeds (system/interface names)
        graph_seeds = self._extract_graph_seeds(natural_query)
        
        # Extract sender/receiver pairs for path queries
        sender_receiver = self._extract_sender_receiver(natural_query)
        
        # Determine query type
        query_type = "graph" if requires_graph else "api"
        
        return {
            "requires_graph": requires_graph,
            "query_type": query_type,
            "graph_seeds": graph_seeds,
            "sender_receiver": sender_receiver,
            "original_query": natural_query
        }
    
    def _llm_based_translation(self, natural_query: str) -> Optional[Dict[str, Any]]:
        """Use LLM to translate natural language to API query"""
        
        system_prompt = build_system_prompt_translation(include_examples=True, sample_interface_count=8)
        
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Translate this to WHINT API query: {natural_query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            query_json = response.choices[0].message.content
            query = json.loads(query_json)
            
            # Validate the generated query
            if self._validate_generated_query(query):
                return query
            else:
                print("Generated query failed validation")
                return None
                
        except Exception as e:
            print(f"LLM query generation failed: {str(e)}")
            return None
    
    def _rule_based_translation(self, natural_query: str) -> Optional[Dict[str, Any]]:
        """Rule-based translation for common query patterns"""
        query_lower = natural_query.lower()
        
        # Determine entity
        entity = self._extract_entity(query_lower)
        if not entity:
            entity = 'inventory'  # Default to inventory
        
        # Check for write operations
        if any(word in query_lower for word in ['create', 'add', 'insert', 'new']):
            return self._handle_create_operation(natural_query, entity)
        elif any(word in query_lower for word in ['update', 'modify', 'change']):
            return self._handle_update_operation(natural_query, entity)
        
        # Handle read operations
        query = {
            "query": {
                "entity": entity,
                "limit": 100,
                "offset": 0
            }
        }
        
        # Extract fields
        fields = self._extract_fields(query_lower, entity)
        if fields:
            query["query"]["fields"] = fields
        
        # Extract filters
        filters = self._extract_filters(query_lower, entity)
        if filters:
            query["query"]["where"] = [{
                "option": 0,  # AND conditions
                "conditions": filters
            }]
        
        # Check for joins/relationships
        joins = self._extract_joins(query_lower)
        if joins:
            query["query"]["with"] = joins
        
        # Extract limit
        limit = self._extract_limit(query_lower)
        if limit:
            query["query"]["limit"] = limit
        
        return query
    
    def _extract_entity(self, query: str) -> Optional[str]:
        """Extract entity from natural language query"""
        for pattern, entity in self.entity_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                return entity
        return None
    
    def _extract_fields(self, query: str, entity: str) -> List[str]:
        """Extract fields to select from query"""
        fields = []
        
        # Look for explicit field mentions
        if 'name' in query and 'name' in self.common_fields.get(entity, []):
            fields.append('name')
        if 'description' in query and 'description' in self.common_fields.get(entity, []):
            fields.append('description')
        if 'type' in query and 'type' in self.common_fields.get(entity, []):
            fields.append('type')
        
        # Check for "show all" or "get all" patterns
        if re.search(r'\b(show|get|list|display)\s+(all|everything)\b', query):
            return []  # Return all fields
        
        return fields
    
    def _extract_filters(self, query: str, entity: str) -> List[Dict[str, Any]]:
        """Extract filter conditions from query"""
        filters = []
        
        # Look for specific value patterns
        # Pattern: "where X is Y" or "with X = Y"
        value_patterns = [
            r'where\s+(\w+)\s+(?:is|equals?|=)\s+["\']?([^"\']+)["\']?',
            r'with\s+(\w+)\s+(?:is|equals?|=)\s+["\']?([^"\']+)["\']?',
            r'(\w+)\s+(?:is|equals?|=)\s+["\']?([^"\']+)["\']?'
        ]
        
        for pattern in value_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                field, value = match.groups()
                if field in self.common_fields.get(entity, []):
                    filters.append({
                        "field": {
                            "name": field,
                            "eq": value.strip()
                        }
                    })
        
        # Look for LIKE patterns
        like_patterns = [
            r'(\w+)\s+(?:contains?|includes?|like)\s+["\']?([^"\']+)["\']?',
            r'find\s+.*?with\s+(\w+).*?["\']([^"\']+)["\']',
            r'search\s+.*?(\w+).*?["\']([^"\']+)["\']'
        ]
        
        for pattern in like_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                field, value = match.groups()
                if field in self.common_fields.get(entity, []):
                    filters.append({
                        "field": {
                            "name": field,
                            "like": value.strip()
                        }
                    })
        
        # Handle inventory type filters
        if entity == 'inventory':
            for type_id, type_name in INVENTORY_TYPES.items():
                if type_name.lower() in query or str(type_id) in query:
                    filters.append({
                        "field": {
                            "name": "type",
                            "eq": str(type_id)
                        }
                    })
                    break
        
        return filters
    
    def _extract_joins(self, query: str) -> List[Dict[str, Any]]:
        """Extract join/relationship requirements"""
        joins = []
        
        # Common relationship keywords
        if any(word in query for word in ['properties', 'property', 'attribute']):
            joins.append({
                "entity": "properties",
                "fields": ["type_id", "value"],
                "with": [{
                    "entity": "type",
                    "fields": ["name", "kind"]
                }]
            })
        
        if any(word in query for word in ['metadata', 'meta']):
            joins.append({
                "entity": "metadata",
                "fields": ["name", "value"]
            })
        
        if any(word in query for word in ['tags', 'tag', 'label']):
            joins.append({
                "entity": "tags",
                "fields": ["value", "tag_id"],
                "with": [{
                    "entity": "tag",
                    "fields": ["name"]
                }]
            })
        
        if any(word in query for word in ['sender', 'source', 'from']):
            joins.append({
                "entity": "sender",
                "fields": ["name", "description"]
            })
        
        if any(word in query for word in ['receiver', 'target', 'to', 'destination']):
            joins.append({
                "entity": "receiver",
                "fields": ["name", "description"]
            })
        
        return joins
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract limit from query"""
        # Look for patterns like "first 10", "top 5", "limit 20"
        patterns = [
            r'\b(?:first|top)\s+(\d+)\b',
            r'\blimit\s+(\d+)\b',
            r'\bshow\s+(\d+)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _handle_create_operation(self, query: str, entity: str) -> Dict[str, Any]:
        """Handle create/insert operations"""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated parsing
        return {
            "upsert": {
                entity: [{
                    "name": "New Item",
                    "description": "Created via natural language"
                }]
            }
        }
    
    def _handle_update_operation(self, query: str, entity: str) -> Dict[str, Any]:
        """Handle update operations"""
        # This is a simplified implementation
        # In practice, you'd need to extract the ID and fields to update
        return {
            "upsert": {
                entity: [{
                    "id": "UPDATE_ID_HERE",
                    "name": "Updated Item"
                }]
            }
        }
    
    def _validate_generated_query(self, query: Dict[str, Any]) -> bool:
        """Validate a generated query"""
        try:
            errors = self.query_builder.validate_query(query)
            return len(errors) == 0
        except Exception:
            return False
    
    def suggest_query_improvements(self, query: str) -> List[str]:
        """Suggest improvements to natural language queries"""
        suggestions = []
        
        query_lower = query.lower()
        
        # Check if entity is specified
        if not any(re.search(pattern, query_lower) for pattern in self.entity_patterns.keys()):
            suggestions.append("Consider specifying what type of data you want (interfaces, tasks, systems, etc.)")
        
        # Check if specific fields are mentioned
        if not any(field in query_lower for field in ['name', 'description', 'type', 'properties', 'metadata']):
            suggestions.append("You can specify which fields to retrieve (name, description, properties, etc.)")
        
        # Check for filtering opportunities
        if not any(word in query_lower for word in ['where', 'with', 'filter', 'having']):
            suggestions.append("You can add filters like 'where type is SAP' or 'with name containing API'")
        
        # Check for limit
        if not re.search(r'\b(?:first|top|limit)\s+\d+\b', query_lower):
            suggestions.append("You can limit results with phrases like 'first 10' or 'limit 50'")
        
        return suggestions
    
    def _extract_graph_seeds(self, query: str) -> List[str]:
        """Extract system/interface names that could be graph seeds"""
        seeds = []
        
        # Look for quoted names
        quoted_pattern = r'"([^"]+)"'
        quoted_matches = re.findall(quoted_pattern, query)
        seeds.extend(quoted_matches)
        
        # Look for TitleCase or UPPERCASE words (likely system names)
        titlecase_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        titlecase_matches = re.findall(titlecase_pattern, query)
        seeds.extend(titlecase_matches)
        
        # Look for common system patterns
        system_patterns = [
            r'\b(SAP\s+\w+)\b',
            r'\b(Salesforce\s+\w*)\b',
            r'\b(SharePoint\s+\w*)\b',
            r'\b(Azure\s+\w*)\b',
            r'\b(AWS\s+\w*)\b',
            r'\b(API\s+\w*)\b',
        ]
        
        for pattern in system_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            seeds.extend(matches)
        
        # Remove duplicates and empty strings
        return list(set([s.strip() for s in seeds if s.strip()]))
    
    def _extract_sender_receiver(self, query: str) -> Optional[Dict[str, str]]:
        """Extract sender and receiver pairs for path queries"""
        query_lower = query.lower()
        
        # Patterns for sender-receiver extraction
        patterns = [
            r'(?:from|sender)\s+["\']?([^"\']+)["\']?\s+(?:to|receiver)\s+["\']?([^"\']+)["\']?',
            r'(?:path|route|connection)\s+(?:from|between)\s+["\']?([^"\']+)["\']?\s+(?:to|and)\s+["\']?([^"\']+)["\']?',
            r'["\']?([^"\']+)["\']?\s+(?:to|and)\s+["\']?([^"\']+)["\']?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                sender, receiver = match.groups()
                return {
                    "sender": sender.strip(),
                    "receiver": receiver.strip()
                }
        
        return None
    
    def generate_example_queries(self) -> List[Dict[str, str]]:
        """Generate example natural language queries"""
        return [
            {
                "query": "Show all SAP interfaces with their properties",
                "description": "Get inventory items containing 'SAP' with property information"
            },
            {
                "query": "Find interfaces where sender is SharePoint",
                "description": "Filter interfaces by sender system"
            },
            {
                "query": "List first 10 tasks with failed runs",
                "description": "Get tasks with unsuccessful execution runs"
            },
            {
                "query": "Get all interfaces of type SAP_IS_CI with metadata",
                "description": "Filter by specific inventory type and include metadata"
            },
            {
                "query": "Show interfaces connecting to API systems",
                "description": "Find interfaces with API-related connections"
            }
        ]
