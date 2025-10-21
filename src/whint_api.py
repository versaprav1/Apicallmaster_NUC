import requests
import json
from typing import Dict, List, Any, Optional
import time
from auth_manager import AuthManager

class WhintAPIClient:
    """WHINT Integration Cockpit API Client with enhanced functionality"""
    
    def __init__(self, base_url: str, auth_manager: AuthManager):
        self.base_url = base_url.rstrip('/')
        self.auth_manager = auth_manager
        self.session = requests.Session()
        self.session.headers.update(self.auth_manager.get_headers())
    
    def execute_query(self, query: Dict[str, Any]) -> Optional[Any]:
        """Execute a query against the WHINT API"""
        try:
            response = self.session.post(
                self.base_url,
                data=json.dumps(query),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")
    
    def execute_paginated_query(self, query: Dict[str, Any], max_records: int = 10000) -> List[Dict[str, Any]]:
        """Execute a paginated query to retrieve all available data"""
        all_results = []
        limit = min(1000, max_records)  # API limit per request
        offset = 0
        
        # Ensure query has pagination parameters
        if "query" not in query:
            query["query"] = {}
        
        base_query = query.copy()
        
        while len(all_results) < max_records:
            # Update pagination parameters
            current_query = json.loads(json.dumps(base_query))  # Deep copy
            current_query["query"]["limit"] = limit
            current_query["query"]["offset"] = offset
            
            try:
                response = self.execute_query(current_query)
                
                # Handle different response formats
                if isinstance(response, dict) and "data" in response:
                    batch = response["data"]
                elif isinstance(response, list):
                    batch = response
                else:
                    batch = []
                
                if not batch:
                    break
                
                all_results.extend(batch)
                
                # If we got fewer results than requested, we've reached the end
                if len(batch) < limit:
                    break
                
                offset += limit
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                # Log error and continue with what we have
                print(f"Pagination error at offset {offset}: {str(e)}")
                break
        
        return all_results[:max_records]
    
    def test_connection(self) -> bool:
        """Test the API connection"""
        try:
            test_query = {
                "query": {
                    "entity": "inventory",
                    "fields": ["id"],
                    "limit": 1
                }
            }
            self.execute_query(test_query)
            return True
        except Exception:
            return False
    
    def get_entity_count(self, entity: str, filters: Optional[List[Dict]] = None) -> int:
        """Get the count of records for an entity"""
        try:
            query = {
                "query": {
                    "entity": entity,
                    "fields": ["id"],
                    "limit": 1
                }
            }
            
            if filters:
                query["query"]["where"] = filters
            
            # First, try to get total count from headers or response
            response = self.session.post(
                self.base_url,
                data=json.dumps(query),
                timeout=30
            )
            response.raise_for_status()
            
            # If the API provides count information, use it
            # Otherwise, we'll need to estimate or do a full query
            data = response.json()
            
            # This is a simplified approach - in practice, you might need
            # to implement a more sophisticated counting mechanism
            return len(data) if isinstance(data, list) else 1
            
        except Exception:
            return 0
    
    def get_inventory_types(self) -> Dict[int, str]:
        """Get available inventory types"""
        # This would ideally come from the API, but we'll use the static mapping
        from inventory_types import INVENTORY_TYPES
        return INVENTORY_TYPES
    
    def validate_entity(self, entity: str) -> bool:
        """Validate if an entity is supported"""
        supported_entities = [
            "inventory", "task", "datasource", "dataFlow", 
            "system", "logEntry", "runs", "properties", 
            "metadata", "tags", "objects", "sender", "receiver"
        ]
        return entity in supported_entities
    
    def validate_field(self, entity: str, field: str) -> bool:
        """Validate if a field is supported for an entity"""
        # This is a basic validation - in practice, you might want to
        # maintain a more comprehensive field mapping
        common_fields = ["id", "create_time", "change_time", "name", "description"]
        entity_specific_fields = {
            "inventory": ["type", "sender_name", "receiver_name", "data_source_id", "object_id"],
            "task": ["start_date", "data_source_id", "type"],
            "datasource": ["type", "category"],
            "logEntry": ["level", "message"],
            "system": ["data_source_id"]
        }
        
        valid_fields = common_fields + entity_specific_fields.get(entity, [])
        return field in valid_fields
    
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get all available data sources"""
        try:
            query = {
                "query": {
                    "entity": "datasource",
                    "fields": ["id", "name", "type", "category"]
                }
            }
            return self.execute_query(query) or []
        except Exception as e:
            print(f"Failed to get data sources: {str(e)}")
            return []
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get a summary of inventory data"""
        try:
            query = {
                "query": {
                    "entity": "inventory",
                    "fields": ["id", "name", "type", "sender_name", "receiver_name"],
                    "limit": 1000
                }
            }
            data = self.execute_query(query)
            
            if not isinstance(data, list):
                return {}
            
            # Generate summary statistics
            summary = {
                "total_count": len(data),
                "by_type": {},
                "top_senders": {},
                "top_receivers": {}
            }
            
            for item in data:
                # Count by type
                item_type = item.get("type", "Unknown")
                summary["by_type"][item_type] = summary["by_type"].get(item_type, 0) + 1
                
                # Count senders
                sender = item.get("sender_name", "Unknown")
                summary["top_senders"][sender] = summary["top_senders"].get(sender, 0) + 1
                
                # Count receivers
                receiver = item.get("receiver_name", "Unknown")
                summary["top_receivers"][receiver] = summary["top_receivers"].get(receiver, 0) + 1
            
            # Sort by count and take top 10
            summary["top_senders"] = dict(sorted(summary["top_senders"].items(), key=lambda x: x[1], reverse=True)[:10])
            summary["top_receivers"] = dict(sorted(summary["top_receivers"].items(), key=lambda x: x[1], reverse=True)[:10])
            
            return summary
            
        except Exception as e:
            print(f"Failed to get inventory summary: {str(e)}")
            return {}
