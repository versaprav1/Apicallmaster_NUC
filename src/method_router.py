"""
Method Router for ApiCallMaster

Routes queries to appropriate methods (graph_rag, vector_rag, db_lookup, API) 
based on intent analysis and configuration.
"""

import os
from typing import Dict, Any, Optional, List
from src.nlp_processor import NLPProcessor


class MethodRouter:
    """Routes queries to appropriate processing methods"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.nlp_processor = NLPProcessor(openai_api_key or os.getenv('OPENAI_API_KEY', ''))
        
        # Load configuration from environment
        self.enabled_methods = os.getenv('METHODS_ENABLED', 'graph_rag,vector_rag,db_lookup,llm_synthesis').split(',')
        self.method_priority = os.getenv('METHOD_PRIORITY', 'graph_rag,vector_rag,db_lookup').split(',')
        self.graph_backend = os.getenv('GRAPH_BACKEND', 'neo4j').lower()
        self.graph_max_hops = int(os.getenv('GRAPH_MAX_HOPS', '2'))
        self.graph_path_limit = int(os.getenv('GRAPH_PATH_LIMIT', '5'))
    
    def route_query(self, user_question: str, data_source: str = "api", **kwargs) -> Dict[str, Any]:
        """
        Route a user question to the appropriate method based on data source and intent
        
        Args:
            user_question: The user's question
            data_source: Data source type ("api", "local_json", "duckdb", "neo4j")
            **kwargs: Additional parameters
        
        Returns:
            Dict with method_name, method_params, and routing_info
        """
        # Analyze query intent
        intent = self.nlp_processor.analyze_query_intent(user_question)
        
        # Determine which method to use based on data source and intent
        method_name = self._select_method(intent, data_source)
        
        # Prepare method parameters
        method_params = self._prepare_method_params(method_name, intent, **kwargs)
        
        return {
            "method_name": method_name,
            "method_params": method_params,
            "routing_info": {
                "intent": intent,
                "data_source": data_source,
                "enabled_methods": self.enabled_methods,
                "method_priority": self.method_priority
            }
        }
    
    def _select_method(self, intent: Dict[str, Any], data_source: str = "api") -> str:
        """
        Select the best method based on intent, data source, and configuration
        
        Data Source Routing:
            - local_json: Always use vector_rag (simple vector search)
            - duckdb: Always use db_lookup (direct SQL queries)
            - neo4j: Always use graph_rag (graph relationships)
            - api: Use intent-based routing with priority
        """
        
        # Explicit data source routing (takes precedence)
        if data_source == "local_json":
            return 'vector_rag'
        
        elif data_source == "duckdb":
            return 'db_lookup'
        
        elif data_source == "neo4j":
            return 'graph_rag'
        
        # API mode: use intent-based routing
        # Only use graph_rag if explicitly required by intent
        if intent.get('requires_graph', False) and 'graph_rag' in self.enabled_methods:
            return 'graph_rag'
        
        # Check method priority order
        for method in self.method_priority:
            if method in self.enabled_methods:
                return method
        
        # Fallback to API if no methods are enabled
        return 'api'
    
    def _prepare_method_params(self, method_name: str, intent: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare parameters for the selected method"""
        
        base_params = {
            "query": intent.get('original_query', ''),
            "intent": intent
        }
        
        if method_name == 'graph_rag':
            return {
                **base_params,
                "max_hops": self.graph_max_hops,
                "path_limit": self.graph_path_limit,
                "graph_seeds": intent.get('graph_seeds', []),
                "sender_receiver": intent.get('sender_receiver'),
                "backend": self.graph_backend
            }
        
        elif method_name == 'vector_rag':
            return {
                **base_params,
                "top_k": kwargs.get('top_k', 5),
                "similarity_threshold": kwargs.get('similarity_threshold', 0.3)
            }
        
        elif method_name == 'db_lookup':
            return {
                **base_params,
                "prompt_templates": kwargs.get('prompt_templates', []),
                "data": kwargs.get('data', [])
            }
        
        elif method_name == 'llm_synthesis':
            return {
                **base_params,
                "summaries_file": kwargs.get('summaries_file'),
                "llm_model": kwargs.get('llm_model'),
                "llm_manager": kwargs.get('llm_manager')
            }
        
        else:  # API fallback
            return {
                **base_params,
                "api_query": self.nlp_processor.translate_to_api_query(intent.get('original_query', ''))
            }
    
    def execute_method(self, method_name: str, method_params: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
        """Execute the selected method with given parameters"""
        
        if method_name == 'graph_rag':
            return self._execute_graph_rag(method_params)
        
        elif method_name == 'vector_rag':
            return self._execute_vector_rag(method_params)
        
        elif method_name == 'db_lookup':
            return self._execute_db_lookup(method_params)
        
        elif method_name == 'llm_synthesis':
            return self._execute_llm_synthesis(method_params)
        
        else:  # API fallback
            return self._execute_api_call(method_params)
    
    def _execute_graph_rag(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Execute graph_rag method"""
        try:
            from methods.graph_rag import run as graph_rag_run
            
            # Extract specific parameters to avoid conflicts
            query = params['query']
            data = params.get('data')
            max_hops = params.get('max_hops', self.graph_max_hops)
            path_limit = params.get('path_limit', self.graph_path_limit)
            llm_model = params.get('llm_model')
            llm_manager = params.get('llm_manager')
            
            # Remove parameters that are already passed explicitly
            remaining_params = {k: v for k, v in params.items() 
                              if k not in ['query', 'data', 'max_hops', 'path_limit', 'llm_model', 'llm_manager']}
            
            result = graph_rag_run(
                query=query,
                data=data,
                max_hops=max_hops,
                path_limit=path_limit,
                llm_model=llm_model,
                llm_manager=llm_manager,
                **remaining_params
            )
            
            # GraphRAG returns (summary_string, meta_dict), so we need to unpack it
            summary, graph_meta = result
            
            return summary, {
                "method": "graph_rag",
                "backend": self.graph_backend,
                "seeds": params.get('graph_seeds', []),
                "sender_receiver": params.get('sender_receiver'),
                **graph_meta  # Include the original GraphRAG metadata
            }
        
        except Exception as e:
            return f"Graph RAG failed: {str(e)}", {
                "method": "graph_rag",
                "error": str(e)
            }
    
    def _execute_vector_rag(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Execute vector_rag method"""
        try:
            from methods.vector_rag import run as vector_rag_run
            
            # Extract specific parameters to avoid conflicts
            query = params['query']
            data = params.get('data')
            top_k = params.get('top_k', 5)
            llm_model = params.get('llm_model')
            llm_manager = params.get('llm_manager')
            
            # Remove parameters that are already passed explicitly
            remaining_params = {k: v for k, v in params.items() 
                              if k not in ['query', 'data', 'top_k', 'llm_model', 'llm_manager']}
            
            result = vector_rag_run(
                query=query,
                data=data,
                top_k=top_k,
                llm_model=llm_model,
                llm_manager=llm_manager,
                **remaining_params
            )
            
            return result, {
                "method": "vector_rag",
                "top_k": params.get('top_k', 5)
            }
        
        except Exception as e:
            return f"Vector RAG failed: {str(e)}", {
                "method": "vector_rag",
                "error": str(e)
            }
    
    def _execute_db_lookup(self, params: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Execute db_lookup method"""
        try:
            from methods.db_lookup import run as db_lookup_run
            
            # Extract specific parameters to avoid conflicts
            query = params['query']
            data = params.get('data', [])
            prompt_templates = params.get('prompt_templates', [])
            
            # Remove parameters that are already passed explicitly
            remaining_params = {k: v for k, v in params.items() 
                              if k not in ['query', 'data', 'prompt_templates']}
            
            result, meta = db_lookup_run(
                query=query,
                data=data,
                prompt_templates=prompt_templates,
                **remaining_params
            )
            
            return result, {
                "method": "db_lookup",
                "meta": meta
            }
        
        except Exception as e:
            return {"error": f"DB Lookup failed: {str(e)}"}, {
                "method": "db_lookup",
                "error": str(e)
            }
    
    def _execute_llm_synthesis(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Execute llm_synthesis method"""
        try:
            from methods.llm_synthesis import run as llm_synthesis_run
            
            # Extract specific parameters to avoid conflicts
            query = params['query']
            data = params.get('data')
            prompt_templates = params.get('prompt_templates', [])
            summaries_file = params.get('summaries_file')
            llm_model = params.get('llm_model')
            llm_manager = params.get('llm_manager')
            
            # Remove parameters that are already passed explicitly
            remaining_params = {k: v for k, v in params.items() 
                              if k not in ['query', 'data', 'prompt_templates', 'summaries_file', 'llm_model', 'llm_manager']}
            
            result, meta = llm_synthesis_run(
                query=query,
                data=data,
                prompt_templates=prompt_templates,
                summaries_file=summaries_file,
                llm_model=llm_model,
                llm_manager=llm_manager,
                **remaining_params
            )
            
            return result, {
                "method": "llm_synthesis",
                "meta": meta
            }
        
        except Exception as e:
            return f"LLM Synthesis failed: {str(e)}", {
                "method": "llm_synthesis",
                "error": str(e)
            }
    
    def _execute_api_call(self, params: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute API call (fallback)"""
        return params.get('api_query', {}), {
            "method": "api",
            "fallback": True
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all enabled methods"""
        status = {
            "enabled_methods": self.enabled_methods,
            "method_priority": self.method_priority,
            "graph_backend": self.graph_backend,
            "method_status": {}
        }
        
        # Check graph_rag health
        if 'graph_rag' in self.enabled_methods:
            try:
                from src.graph_store_neo4j import Neo4jGraphStore
                store = Neo4jGraphStore()
                result = store.run_tx("MATCH (n) RETURN count(n) as total")
                total_nodes = result[0]['total'] if result else 0
                store.close()
                
                status["method_status"]["graph_rag"] = {
                    "status": "healthy" if total_nodes > 0 else "empty_graph",
                    "total_nodes": total_nodes
                }
            except Exception as e:
                status["method_status"]["graph_rag"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Check other methods
        for method in ['vector_rag', 'db_lookup', 'llm_synthesis']:
            if method in self.enabled_methods:
                status["method_status"][method] = {
                    "status": "available"
                }
        
        return status


