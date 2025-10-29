import streamlit as st
# Ensure page config is the first Streamlit command
st.set_page_config(
    page_title="WHINT API AI Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)
import os
import requests
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from openai import OpenAI
import base64
from pathlib import Path
from src.llm_helper import get_available_providers, get_best_available_model, generate_llm_response, should_use_chunking
from src.knowledge_store import KnowledgeStore
from src.vector_knowledge_store import VectorKnowledgeStore
from src.llm_providers import LLMProviderManager
from dotenv import load_dotenv
import re
from src.prompt_builder import build_system_prompt_translation, build_system_prompt_synthesis
from src.method_router import MethodRouter
from src.response_logger import ResponseLogger
from local_executor.loader import iter_records
from local_executor.router import select_collection
from local_executor.executor import execute_query
from local_executor.adapters import to_api_response
from duckdb_engine.executor import DuckDBExecutor
"""Watcher configuration to prevent FileNotFoundError on __pycache__ (Streamlit watchdog race).
Switch to polling-based file watcher, which is more stable on Windows and avoids races
when temporary .pyc files are created/removed during edits.
"""
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "poll")

load_dotenv()

def load_credentials_from_sources():
    """Load credentials from multiple sources in priority order"""
    credentials = {}
    
    # Priority 1: Environment variables
    if os.getenv('WHINT_API_BASE_URL'):
        credentials = {
            'api_url': os.getenv('WHINT_API_BASE_URL'),
            'api_key': os.getenv('WHINT_API_X_API_KEY'),
            'username': os.getenv('WHINT_USERNAME'),
            'password': os.getenv('WHINT_PASSWORD'),
            'openai_key': os.getenv('OPENAI_API_KEY')
        }
    
    # Priority 2: Streamlit secrets
    try:
        if hasattr(st, 'secrets') and 'whint_api' in st.secrets:
            secrets_creds = {
                'api_url': st.secrets.get('whint_api', {}).get('base_url'),
                'api_key': st.secrets.get('whint_api', {}).get('x_api_key'),
                'username': st.secrets.get('whint_api', {}).get('username'),
                'password': st.secrets.get('whint_api', {}).get('password'),
                'openai_key': st.secrets.get('openai', {}).get('api_key')
            }
            if all(secrets_creds.values()):
                credentials = secrets_creds
    except Exception:
        pass
    
    # Priority 3: Local .env file (via python-dotenv)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv('WHINT_API_BASE_URL'):
            credentials = {
                'api_url': os.getenv('WHINT_API_BASE_URL'),
                'api_key': os.getenv('WHINT_API_X_API_KEY'),
                'username': os.getenv('WHINT_USERNAME'),
                'password': os.getenv('WHINT_PASSWORD'),
                'openai_key': os.getenv('OPENAI_API_KEY')
            }
    except ImportError:
        pass
    
    return credentials

def save_credentials_to_local_file(credentials: Dict[str, Any]):
    """Save credentials to local .env file for persistence"""
    try:
        env_content = f"""# WHINT API Credentials - Auto-saved
WHINT_API_BASE_URL={credentials.get('api_url', '')}
WHINT_API_X_API_KEY={credentials.get('api_key', '')}
WHINT_USERNAME={credentials.get('username', '')}
WHINT_PASSWORD={credentials.get('password', '')}
OPENAI_API_KEY={credentials.get('openai_key', '')}
GEMINI_API_KEY={credentials.get('gemini_key', '')}
ANTHROPIC_API_KEY={credentials.get('anthropic_key', '')}
GROQ_API_KEY={credentials.get('groq_key', '')}
OPENROUTER_API_KEY={credentials.get('openrouter_key', '')}
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        return True
    except Exception:
        return False

def initialize_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'credentials' not in st.session_state:
        # Try to load from persistent sources
        stored_credentials = load_credentials_from_sources()
        if stored_credentials and all(stored_credentials.values()):
            st.session_state.credentials = stored_credentials
            st.session_state.authenticated = True
        else:
            st.session_state.credentials = {}
    if 'credential_source' not in st.session_state:
        st.session_state.credential_source = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    if 'knowledge_store' not in st.session_state:
        st.session_state.knowledge_store = KnowledgeStore()
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = VectorKnowledgeStore()
    if 'result_saver' not in st.session_state:
        try:
            import sys
            import os
            # Add current directory to path if not already there
            if os.getcwd() not in sys.path:
                sys.path.insert(0, os.getcwd())
            from src.result_saver import ResultSaver
            st.session_state.result_saver = ResultSaver()
        except ImportError as e:
            # Fallback: create a simple result saver
            class SimpleResultSaver:
                def __init__(self):
                    self.results = []
                
                def save_result(self, question, answer, method, model, data_source, metadata=None):
                    result = {
                        "id": len(self.results) + 1,
                        "timestamp": datetime.now().isoformat(),
                        "question": question,
                        "answer": answer,
                        "method": method,
                        "model": model,
                        "data_source": data_source,
                        "metadata": metadata or {}
                    }
                    self.results.append(result)
                    return result["id"]
                
                def get_all_results(self):
                    return self.results
                
                def get_stats(self):
                    if not self.results:
                        return {"total": 0}
                    return {"total": len(self.results)}
            
            st.session_state.result_saver = SimpleResultSaver()
    if 'llm_manager' not in st.session_state:
        st.session_state.llm_manager = LLMProviderManager()
    if 'method_router' not in st.session_state:
        st.session_state.method_router = MethodRouter(st.session_state.credentials.get('openai_key', ''))
    if 'response_logger' not in st.session_state:
        st.session_state.response_logger = ResponseLogger()

def validate_credentials(api_url: Optional[str], api_key: Optional[str], username: Optional[str], password: Optional[str]) -> tuple[bool, str]:
    """Test API credentials with detailed error reporting"""
    if not all([api_url, api_key, username, password]):
        return False, "Missing required credentials"
    
    # Cast to strings for type safety
    api_url_str = str(api_url)
    api_key_str = str(api_key)
    username_str = str(username)
    password_str = str(password)
    
    try:
        # Test 1: Check if API URL is reachable
        try:
            base_response = requests.get(api_url_str, timeout=5)
        except requests.exceptions.ConnectionError:
            return False, "❌ API URL unreachable - Check your network connection or API base URL"
        except requests.exceptions.Timeout:
            return False, "❌ API URL timeout - Server not responding"
        except Exception as e:
            return False, f"❌ API URL error: {str(e)}"
        
        # Test 2: Try with correct WHINT API structure
        headers = {
            'x-api-key': api_key_str,
            'Content-Type': 'application/json'
        }
        
        test_query = {
            "query": {
                "entity": "inventory",
                "fields": ["id"],
                "limit": 1
            }
        }
        
        response = requests.post(
            f"{api_url_str}/interfaces",
            headers=headers,
            auth=(username_str, password_str),
            json=test_query,
            timeout=10
        )
        
        # Analyze response status codes
        if response.status_code == 401:
            if 'x-api-key' in response.text.lower() or 'api key' in response.text.lower():
                return False, "❌ X-API-Key is invalid - Check your API key"
            else:
                return False, "❌ Username/Password authentication failed - Check credentials"
        elif response.status_code == 403:
            return False, "❌ Access forbidden - Your account may not have API access permissions"
        elif response.status_code == 404:
            return False, "❌ API endpoint not found - Check your API base URL"
        elif response.status_code == 500:
            return False, "❌ Server error - WHINT API is experiencing issues"
        elif response.status_code in [200, 201]:
            return True, "✅ All credentials valid - Connection successful"
        else:
            return False, f"❌ Unexpected response (Status {response.status_code}): {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timeout - API server not responding"
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection failed - Check network or API URL"
    except Exception as e:
        return False, f"❌ Connection test failed: {str(e)}"

def create_api_query(user_question: str, selected_model: Optional[str] = None) -> Dict[str, Any]:
    """Use selected LLM provider to translate user question to WHINT API query"""
    try:
        # Get LLM manager and update environment variables
        llm_manager = st.session_state.llm_manager
        credentials = st.session_state.get('credentials', {})
        
        # Set environment variables for LLM providers
        if credentials.get('openai_key'):
            os.environ['OPENAI_API_KEY'] = credentials['openai_key']
        if credentials.get('gemini_key'):
            os.environ['GEMINI_API_KEY'] = credentials['gemini_key']
        if credentials.get('anthropic_key'):
            os.environ['ANTHROPIC_API_KEY'] = credentials['anthropic_key']
        if credentials.get('groq_key'):
            os.environ['GROQ_API_KEY'] = credentials['groq_key']
        if credentials.get('openrouter_key'):
            os.environ['OPENROUTER_API_KEY'] = credentials['openrouter_key']
        
        # Reinitialize clients with new environment variables
        llm_manager.initialize_clients()
        
        # Determine which model to use
        if selected_model == "Auto-select best model" or not selected_model:
            # Auto-select based on available models
            available_models = llm_manager.get_available_models()
            if not available_models:
                raise Exception("No LLM providers available. Please add API keys in credentials.")
            
            # Prefer high-context models for query translation
            high_context = llm_manager.get_high_context_models(min_context=100000)
            if high_context:
                model_name = next(iter(high_context.keys()))
            else:
                model_name = next(iter(available_models.keys()))
        else:
            model_name = selected_model
        
        # Use centralized prompt builder
        system_prompt = build_system_prompt_translation(include_examples=True, sample_interface_count=8)
        
        response_text = llm_manager.generate_response(
            model_name,
            system_prompt,
            user_question,
            temperature=0.1,
            max_tokens=2048
        )
        if response_text:
            result = parse_llm_response(response_text)
            if isinstance(result, dict) and not result.get("error"):
                return result
            # Retry: stricter formatting
            retry_prompt = system_prompt + "\nCRITICAL: Return ONLY valid minified JSON. No prose, no markdown."
            retry_text = llm_manager.generate_response(
                model_name,
                retry_prompt,
                f"USER REQUEST: {user_question}\nReturn only JSON for the query.",
                temperature=0.0,
                max_tokens=1024
            )
            if retry_text:
                retry_result = parse_llm_response(retry_text)
                if isinstance(retry_result, dict) and not retry_result.get("error"):
                    return retry_result
            # Fallback: safe default query
            st.warning("LLM did not return valid JSON. Falling back to a safe default query.")
            uq = user_question.lower() if isinstance(user_question, str) else ""
            type_ids = None
            if "sap" in uq:
                type_ids = ["14","15","16","17","18","19","20"]
            elif "mule" in uq:
                type_ids = ["0","1"]
            elif "azure" in uq:
                type_ids = ["3","4","5","6","7","8"]
            elif "apim" in uq:
                type_ids = ["2"]
            
            # Check if user wants "all" interfaces
            wants_all = any(word in uq for word in ["all", "every", "complete", "entire", "full"])
            
            base_query: Dict[str, Any] = {
                "query": {
                    "entity": "inventory",
                    "fields": ["name", "sender_name", "receiver_name", "description", "type"]
                }
            }
            
            # Only add limit if not requesting "all"
            if not wants_all:
                base_query["query"]["limit"] = 300
                
            if type_ids:
                base_query["query"]["where"] = [{
                    "option": 1,
                    "conditions": [{
                        "field": {"name": "type", "in": type_ids}
                    }]
                }]
            return base_query
        return {}
    except Exception as e:
        st.error(f"Failed to create API query: {str(e)}")
        return {}

def execute_api_query(query: Dict[str, Any], credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Execute query against WHINT API with type-specific endpoints"""
    try:
        headers = {
            'x-api-key': credentials['api_key'],
            'Content-Type': 'application/json'
        }
        
        # Determine endpoint based on query type
        endpoint = determine_api_endpoint(query, credentials['api_url'])
        
        # Display the actual endpoint being used
        st.info(f"🔗 API Endpoint: {endpoint}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            auth=(credentials['username'], credentials['password']),
            json=query,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API request failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"API request error: {str(e)}")
        return None

def execute_query_locally(query: Dict[str, Any], endpoint: str, file_path: str) -> Optional[Dict[str, Any]]:
    try:
        records = iter_records(file_path)
        collection = select_collection(records, endpoint)
        items = execute_query(collection, {"query": query.get("query", {})})
        return to_api_response(items)
    except Exception as e:
        st.error(f"Local execution failed: {str(e)}")
        return None

def determine_api_endpoint(query: Dict[str, Any], base_url: str) -> str:
    """Determine the correct API endpoint based on query type"""
    # Type-specific endpoint mapping for inventory (interfaces)
    type_endpoints = {
        'sap': '/sap',
        'mule': '/mule', 
        'azure': '/azure',
        'apim': '/apim'
    }
    
    # Entity-to-endpoint mapping for non-inventory entities
    entity_endpoints = {
        'task': '/tasks',
        'logEntry': '/logs',
        'datasource': '/datasources',
        'system': '/systems',
        'dataFlow': '/dataflows'
    }
    
    # Handle upsert payloads explicitly
    if isinstance(query, dict) and 'upsert' in query:
        try:
            upsert_block = query.get('upsert', {})
            if isinstance(upsert_block, dict) and upsert_block:
                upsert_entity = next(iter(upsert_block.keys()))
                if upsert_entity in entity_endpoints:
                    return f"{base_url}{entity_endpoints[upsert_entity]}/upsert"
                # default upsert to inventory if unspecified/supported
                if upsert_entity == 'inventory' or upsert_entity is None:
                    return f"{base_url}/inventory/upsert"
                # fallback generic
                return f"{base_url}/{upsert_entity}/upsert"
        except Exception:
            # Fallback generic upsert
            return f"{base_url}/inventory/upsert"
    
    # Try entity-based routing first
    try:
        entity = query.get('query', {}).get('entity') if isinstance(query, dict) else None
        if entity in entity_endpoints:
            return f"{base_url}{entity_endpoints[entity]}"
    except Exception:
        pass
    
    # Existing logic: inspect inventory type filters to route to interfaces sub-endpoints
    try:
        if 'query' in query and 'where' in query['query']:
            conditions = query['query']['where']
            for condition_group in conditions:
                if 'conditions' in condition_group:
                    for condition in condition_group['conditions']:
                        if 'field' in condition and condition['field'].get('name') == 'type':
                            field_data = condition['field']
                            # Handle "eq" operator (single type)
                            if 'eq' in field_data:
                                type_value = field_data['eq']
                                type_ids = [int(type_value)]
                            # Handle "in" operator (multiple types)
                            elif 'in' in field_data:
                                type_values = field_data['in']
                                type_ids = [int(t) for t in type_values]
                            else:
                                continue
                            # Determine endpoint based on type IDs
                            for type_id in type_ids:
                                # SAP types: 14-20
                                if 14 <= type_id <= 20:
                                    return f"{base_url}/interfaces{type_endpoints['sap']}"
                                # MULE types: 0-1
                                elif 0 <= type_id <= 1:
                                    return f"{base_url}/interfaces{type_endpoints['mule']}"
                                # AZURE types: 3-8  
                                elif 3 <= type_id <= 8:
                                    return f"{base_url}/interfaces{type_endpoints['azure']}"
                                # APIM type: 2
                                elif type_id == 2:
                                    return f"{base_url}/interfaces{type_endpoints['apim']}"
    except Exception:
        pass
    
    # Defaults
    # - For general inventory queries, retain existing default to /interfaces
    # - For unknown entities, fall back to /interfaces to avoid breaking existing behavior
    return f"{base_url}/interfaces"

def analyze_user_intent(user_question: str) -> str:
    """Analyze user question to determine intent: list_all, count, search, or analyze"""
    question_lower = user_question.lower()
    
    # List all patterns
    list_patterns = ["list all", "show all", "get all", "display all", "all interfaces", "all items"]
    if any(pattern in question_lower for pattern in list_patterns):
        return "list_all"
    
    # Count patterns  
    count_patterns = ["count", "how many", "number of", "total number", "how many are there"]
    if any(pattern in question_lower for pattern in count_patterns):
        return "count"
    
    # Search patterns
    search_patterns = ["find", "search", "look for", "show me", "get me", "where is", "which"]
    if any(pattern in question_lower for pattern in search_patterns):
        return "search"
    
    # Default to analyze for complex questions
    return "analyze"

def generate_list_response(api_response: Dict[str, Any], user_question: str) -> str:
    """Generate a direct list response without summarization"""
    try:
        data_items = []
        if isinstance(api_response, dict) and 'data' in api_response:
            data_items = api_response['data']
        elif isinstance(api_response, list):
            data_items = api_response
            
        if not data_items:
            return "No items found."
        
        total_count = len(data_items)
        response = f"# Complete List of Interfaces\n\n**Total: {total_count} interfaces**\n\n"
        
        # For very large lists, show first 100 and indicate truncation
        display_items = data_items[:100] if total_count > 100 else data_items
        
        for i, item in enumerate(display_items, 1):
            name = item.get('name', item.get('norm_name', 'Unknown'))
            item_type = item.get('type', item.get('norm_type', 'Unknown'))
            sender = item.get('sender_name', item.get('norm_sender_name', ''))
            receiver = item.get('receiver_name', item.get('norm_receiver_name', ''))
            
            response += f"{i}. **{name}**\n"
            if item_type != 'Unknown':
                response += f"   - Type: {item_type}\n"
            if sender:
                response += f"   - Sender: {sender}\n"
            if receiver:
                response += f"   - Receiver: {receiver}\n"
            response += "\n"
        
        if total_count > 100:
            response += f"\n*Showing first 100 of {total_count} interfaces. Use a more specific query to see more.*"
        
        return response
    except Exception as e:
        return f"Error generating list response: {str(e)}"

def generate_count_response(api_response: Dict[str, Any], user_question: str) -> str:
    """Generate a direct count response"""
    try:
        data_items = []
        if isinstance(api_response, dict) and 'data' in api_response:
            data_items = api_response['data']
        elif isinstance(api_response, list):
            data_items = api_response
            
        total_count = len(data_items)
        
        # Try to get more specific counts by type if available
        type_counts = {}
        for item in data_items:
            item_type = item.get('type', item.get('norm_type', 'Unknown'))
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        response = f"# Count Results\n\n**Total: {total_count} interfaces**\n\n"
        
        if len(type_counts) > 1:
            response += "**Breakdown by type:**\n"
            for item_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                response += f"- {item_type}: {count}\n"
        
        return response
    except Exception as e:
        return f"Error generating count response: {str(e)}"

def generate_search_response(api_response: Dict[str, Any], user_question: str) -> str:
    """Generate a direct search response showing matching items"""
    try:
        data_items = []
        if isinstance(api_response, dict) and 'data' in api_response:
            data_items = api_response['data']
        elif isinstance(api_response, list):
            data_items = api_response
            
        if not data_items:
            return "No matching items found."
        
        total_count = len(data_items)
        response = f"# Search Results\n\n**Found {total_count} matching interfaces**\n\n"
        
        # Show first 50 results
        display_items = data_items[:50] if total_count > 50 else data_items
        
        for i, item in enumerate(display_items, 1):
            name = item.get('name', item.get('norm_name', 'Unknown'))
            item_type = item.get('type', item.get('norm_type', 'Unknown'))
            description = item.get('description', item.get('norm_description', ''))
            
            response += f"{i}. **{name}**\n"
            if item_type != 'Unknown':
                response += f"   - Type: {item_type}\n"
            if description:
                response += f"   - Description: {description}\n"
            response += "\n"
        
        if total_count > 50:
            response += f"\n*Showing first 50 of {total_count} results.*"
        
        return response
    except Exception as e:
        return f"Error generating search response: {str(e)}"

def analyze_response_direct(user_question: str, api_response: Dict[str, Any], openai_api_key: str) -> str:
    """Direct analysis without chunking for smaller responses"""
    try:
        llm_manager = st.session_state.llm_manager
        selected_model = st.session_state.selected_model
        
        system_prompt = """You are an expert at analyzing WHINT Integration Cockpit data.
        
        Analyze the API response and provide a clear, structured answer to the user's question.
        Focus on the key insights and present the information in an easy-to-understand format.
        
        If the data contains multiple items, summarize the key patterns and highlight important details.
        Use bullet points and clear sections to organize your response."""
        
        response_text = json.dumps(api_response, indent=2)
        user_prompt = f"""
        User Question: {user_question}
        
        API Response: {response_text}
        
        Please analyze this data and provide a structured response to the user's question.
        """
        
        response_text = llm_manager.generate_response(
            selected_model,
            system_prompt,
            user_prompt,
            temperature=0.1,
            max_tokens=2048
        )
        return response_text or "No analysis available"
    except Exception as e:
        return f"Failed to analyze response: {str(e)}"

def analyze_response(user_question: str, api_response: Dict[str, Any], openai_api_key: str) -> str:
    """Use LLMProviderManager to analyze API response and provide structured answer with intelligent intent-based processing"""
    try:
        llm_manager = st.session_state.llm_manager
        selected_model = st.session_state.selected_model
        
        # Analyze user intent first
        intent = analyze_user_intent(user_question)
        
        # Convert response to string for token estimation
        response_text = json.dumps(api_response, indent=2)
        estimated_tokens = len(response_text) // 4
        
        # Get result count
        total_items = 0
        if isinstance(api_response, dict) and 'data' in api_response:
            total_items = len(api_response.get('data', []))
        elif isinstance(api_response, list):
            total_items = len(api_response)
        
        # For large datasets (>100 items), use chunked analysis regardless of intent
        if total_items > 100 or estimated_tokens > 25000:
            st.info(f"📊 Large dataset detected ({total_items} items). Using smart chunked analysis...")
            return analyze_response_chunked(user_question, api_response, openai_api_key)
        
        # Handle different intents intelligently for smaller datasets
        if intent == "list_all":
            return generate_list_response(api_response, user_question)
        elif intent == "count":
            return generate_count_response(api_response, user_question)
        elif intent == "search":
            return generate_search_response(api_response, user_question)
        elif intent == "analyze":
            # For smaller analysis requests, use direct analysis
            return analyze_response_direct(user_question, api_response, openai_api_key)
        else:
            # Default to direct analysis for unknown intents
            return analyze_response_direct(user_question, api_response, openai_api_key)
    except Exception as e:
        return f"Failed to analyze response: {str(e)}"


def analyze_response_chunked(user_question: str, api_response: Dict[str, Any], openai_api_key: str) -> str:
    """Process large API responses in chunks to avoid token limits"""
    try:
        llm_manager = st.session_state.llm_manager
        selected_model = st.session_state.selected_model
        # Debug print to confirm which LLM is used
        print(f"[DEBUG] Using LLM for chunking: {selected_model}")
        st.info(f"[DEBUG] Using LLM for chunking: {selected_model}")
        # Extract the data array from the response
        data_items = []
        if isinstance(api_response, dict):
            if 'data' in api_response and isinstance(api_response['data'], list):
                data_items = list(api_response['data'])
        elif isinstance(api_response, list):
            data_items = list(api_response)
        if not data_items:
            return "No data items found in the API response to analyze."
        # Calculate chunk size (aim for ~20k tokens per chunk)
        total_items = len(data_items)
        # For large datasets, use larger chunks to reduce total number of chunks
        if total_items > 1000:
            chunk_size = max(200, min(500, total_items // 20))  # Larger chunks for big datasets
        else:
            chunk_size = max(10, min(100, total_items // 10))  # Smaller chunks for small datasets
        chunk_summaries = []
        # Show progress indicator
        st.info(f"Processing large response in chunks... Found {total_items} items to analyze.")
        progress_bar = st.progress(0.0)
        # Process each chunk
        for i in range(0, total_items, chunk_size):
            chunk = data_items[i:i + chunk_size]
            chunk_text = json.dumps(chunk, indent=2)
            # Update progress
            progress = min(1.0, (i + chunk_size) / total_items)
            progress_bar.progress(progress)
            st.write(f"Processing chunk {len(chunk_summaries)+1}: items {i+1}-{min(i+chunk_size, total_items)}")
            chunk_prompt = f"""
            Analyze this chunk of WHINT API data (items {i+1}-{min(i+chunk_size, total_items)} of {total_items}).
            
            USER QUESTION: {user_question}
            
            CHUNK DATA:
            {chunk_text}
            
            Provide a brief summary of this chunk including:
            - Key items that match the user's question
            - Important patterns or characteristics
            - Notable data points
            
            Keep the summary concise but informative.
            """
            try:
                chunk_summary = llm_manager.generate_response(
                    selected_model,
                    "You are analyzing a chunk of API data. Be concise but thorough.",
                    chunk_prompt,
                    temperature=0.1,
                    max_tokens=2048
                )
                chunk_summaries.append(f"**Chunk {len(chunk_summaries)+1} (Items {i+1}-{min(i+chunk_size, total_items)}):**\n{chunk_summary}")
            except Exception as e:
                chunk_summaries.append(f"**Chunk {len(chunk_summaries)+1}:** Error processing chunk: {str(e)}")
        # Complete progress
        progress_bar.progress(1.0)
        st.success(f"✅ Processed all {total_items} items in {len(chunk_summaries)} chunks. Creating final summary...")
        # Now create final summary from all chunks
        # If we have too many chunks, use hierarchical summarization
        if len(chunk_summaries) > 20:
            st.info("Using hierarchical summarization for large number of chunks...")
            # First, summarize chunks in groups
            group_size = 10
            grouped_summaries = []
            for i in range(0, len(chunk_summaries), group_size):
                group = chunk_summaries[i:i + group_size]
                group_prompt = f"""
                Summarize these {len(group)} chunk summaries from a WHINT API analysis:
                
                {chr(10).join(group)}
                
                Provide a concise summary of the key findings from these chunks.
                """
                try:
                    group_summary = llm_manager.generate_response(
                        selected_model,
                        "You are summarizing a group of chunk summaries.",
                        group_prompt,
                        temperature=0.1,
                        max_tokens=1024
                    )
                    grouped_summaries.append(f"**Group {len(grouped_summaries)+1}:** {group_summary}")
                except Exception as e:
                    grouped_summaries.append(f"**Group {len(grouped_summaries)+1}:** Error: {str(e)}")
            
            # Now create final summary from grouped summaries
            final_summaries = grouped_summaries
        else:
            final_summaries = chunk_summaries
        
        final_prompt = f"""
        Based on these summaries from a WHINT API response, provide a comprehensive answer to the user's question.
        
        USER QUESTION: {user_question}
        
        SUMMARIES:
        {chr(10).join(final_summaries)}
        
        TOTAL ITEMS PROCESSED: {total_items}
        
        Please provide:
        1. A direct answer to the user's question
        2. Overall statistics and key insights
        3. Summary of important patterns across all data
        4. Recommendations or notable findings
        
        Format your response clearly and mention that this analysis was performed on {total_items} items.
        """
        final_summary = llm_manager.generate_response(
            selected_model,
            "You are providing a final comprehensive analysis based on summaries.",
            final_prompt,
            temperature=0.1,
            max_tokens=4096  # Increased token limit for final summary
        )
        return final_summary or "No analysis available"
    except Exception as e:
        return f"Failed to analyze response in chunks: {str(e)}"

def parse_llm_response(raw_response):
    """Robustly extract and parse JSON from LLM responses."""
    # Strategy 1: Try direct parsing
    try:
        return json.loads(raw_response)
    except Exception:
        pass
    # Strategy 2: Remove markdown code blocks and trailing undefined/null
    cleaned = raw_response.strip()
    cleaned = re.sub(r'```[a-zA-Z]*', '', cleaned)  # Remove code block markers like ```json
    cleaned = cleaned.replace('```', '')
    cleaned = re.sub(r'(undefined|null)\s*$', '', cleaned)
    cleaned = cleaned.strip()
    # Strategy 3: Extract only the JSON part
    json_start = cleaned.find('{')
    json_end = cleaned.rfind('}')
    if json_start != -1 and json_end != -1 and json_end > json_start:
        cleaned = cleaned[json_start:json_end + 1]
        try:
            return json.loads(cleaned)
        except Exception:
            pass
    # Strategy 4: Regex fallback
    match = re.search(r'({[\s\S]*})', cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Strategy 5: Return error structure
    return {
        "error": "Failed to parse JSON",
        "raw_response": raw_response,
        "parsed": False
    }

def credentials_page():
    """Display credentials input page"""
    st.title("🔍 WHINT API AI Assistant")
    st.markdown("---")
    
    # Check if credentials are already saved
    saved_creds = st.session_state.get('credentials', {})
    
    if saved_creds:
        st.markdown("### Saved Credentials")
        st.info("Your credentials are saved for this session. You can update them below or disconnect.")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Continue with Saved Credentials", type="primary"):
                st.session_state.authenticated = True
                st.rerun()
        
        with col2:
            if st.button("Clear Saved Credentials", type="secondary"):
                st.session_state.credentials = {}
                st.session_state.authenticated = False
                st.session_state.chat_history = []
                st.success("Credentials cleared!")
                st.rerun()
        
        st.markdown("---")
    
    # Show credential storage options
    st.markdown("### Credential Storage Options")
    st.info("""
    **Available credential storage methods:**
    - **Session Storage** (current): Credentials saved until you close the app
    - **Environment Variables**: Store in .env file for permanent local storage
    - **Streamlit Secrets**: For production deployments with secrets.toml
    - **System Environment**: Set globally on your system
    
    Choose your preferred method below.
    """)
    
    storage_method = st.selectbox(
        "Credential Storage Method",
        ["Session Only", "Save to .env File", "Use Streamlit Secrets", "Manual Entry"],
        help="Choose how to store your credentials for future sessions"
    )
    
    st.markdown("### Enter Your API Credentials")
    st.markdown("Please provide your WHINT Integration Cockpit API credentials to get started.")
    
    with st.form("credentials_form"):
        api_url = st.text_input(
            "API Base URL",
            value=saved_creds.get('api_url', "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"),
            help="WHINT API base URL"
        )
        api_key = st.text_input(
            "X-API-Key",
            value=saved_creds.get('api_key', ""),
            type="password",
            help="Your WHINT API key"
        )
        username = st.text_input(
            "Username",
            value=saved_creds.get('username', ""),
            help="Your WHINT username"
        )
        password = st.text_input(
            "Password",
            value=saved_creds.get('password', ""),
            type="password",
            help="Your WHINT password"
        )
        openai_key = st.text_input(
            "OpenAI API Key",
            value=saved_creds.get('openai_key', ""),
            type="password",
            help="Your OpenAI API key"
        )
        gemini_key = st.text_input(
            "Gemini API Key",
            value=saved_creds.get('gemini_key', ""),
            type="password",
            help="Your Gemini API key"
        )
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=saved_creds.get('anthropic_key', ""),
            type="password",
            help="Your Anthropic API key"
        )
        groq_key = st.text_input(
            "Groq API Key",
            value=saved_creds.get('groq_key', ""),
            type="password",
            help="Your Groq API key"
        )
        openrouter_key = st.text_input(
            "OpenRouter API Key",
            value=saved_creds.get('openrouter_key', ""),
            type="password",
            help="Your OpenRouter API key"
        )
        col1, col2 = st.columns(2)
        with col1:
            save_and_test = st.form_submit_button("Save & Test", type="primary")
        with col2:
            session_and_test = st.form_submit_button("Use for This Session Only & Test", type="secondary")

    if save_and_test or session_and_test:
        credentials = {
            'api_url': api_url,
            'api_key': api_key,
            'username': username,
            'password': password,
            'openai_key': openai_key,
            'gemini_key': gemini_key,
            'anthropic_key': anthropic_key,
            'groq_key': groq_key,
            'openrouter_key': openrouter_key
        }
        # Test connection before saving
        if all([api_url, api_key, username, password]):
            with st.spinner("Testing WHINT API connection..."):
                is_valid, message = validate_credentials(api_url, api_key, username, password)
                if is_valid:
                    st.success(message)
                    st.session_state.credentials = credentials
                    st.session_state.authenticated = True
                    # Update environment variables for all LLM providers
                    for key, env_var in [
                        ('openai_key', 'OPENAI_API_KEY'),
                        ('gemini_key', 'GEMINI_API_KEY'),
                        ('anthropic_key', 'ANTHROPIC_API_KEY'),
                        ('groq_key', 'GROQ_API_KEY'),
                        ('openrouter_key', 'OPENROUTER_API_KEY'),
                    ]:
                        if key in credentials and credentials[key]:
                            os.environ[env_var] = credentials[key]
                    st.session_state.llm_manager.initialize_clients()
                    if save_and_test:
                        if save_credentials_to_local_file(credentials):
                            st.success("✅ Credentials saved to .env file for future sessions")
                        else:
                            st.warning("⚠️ Could not save to .env file, using session storage only")
                    else:
                        st.info("Credentials will be used for this session only and will not be saved to .env file.")
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.error("Please fill in API URL, X-API-Key, Username, and Password to test connection.")
    
    # Show setup instructions for different storage methods
    if storage_method == "Use Streamlit Secrets":
        st.markdown("### Streamlit Secrets Setup")
        st.code("""
# Create .streamlit/secrets.toml file with:
[whint_api]
base_url = "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
x_api_key = "your_api_key_here"
username = "your_username_here"
password = "your_password_here"

[openai]
api_key = "your_openai_key_here"
        """, language="toml")
    
    elif storage_method == "Save to .env File":
        st.markdown("### Environment File Setup")
        st.info("Your credentials will be automatically saved to a .env file when you connect. This file will be used for future sessions.")
        
    elif storage_method == "Manual Entry":
        st.markdown("### System Environment Variables")
        st.code("""
# Set these environment variables on your system:
export WHINT_API_BASE_URL="https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
export WHINT_API_X_API_KEY="your_api_key_here"
export WHINT_USERNAME="your_username_here"
export WHINT_PASSWORD="your_password_here"
export OPENAI_API_KEY="your_openai_key_here"
        """, language="bash")

def analyze_user_intent(user_question: str) -> str:
    """Analyze user's intent to determine appropriate response type"""
    question_lower = user_question.lower().strip()
    
    # Intent patterns
    list_patterns = [
        'list all', 'show all', 'give me all', 'display all',
        'list interfaces', 'show interfaces', 'all interfaces',
        'names of', 'interface names', 'what are the'
    ]
    
    count_patterns = [
        'how many', 'count', 'number of', 'total'
    ]
    
    search_patterns = [
        'find', 'search', 'look for', 'contains', 'with name',
        'where', 'that have', 'matching'
    ]
    
    # Check for list intent
    for pattern in list_patterns:
        if pattern in question_lower:
            return "list_names"
    
    # Check for count intent
    for pattern in count_patterns:
        if pattern in question_lower:
            return "count"
    
    # Check for search intent
    for pattern in search_patterns:
        if pattern in question_lower:
            return "specific_search"
    
    # Default to analysis/summary
    return "analysis"

def generate_list_response(cache: Dict[str, Any], user_question: str, api_endpoint: str) -> str:
    """Generate a list response from cached data"""
    try:
        # First try to get entity strings (which have comprehensive data)
        entity_strings = cache.get('entity_strings', [])
        
        if entity_strings:
            # Extract names from entity strings
            import re
            names = set()
            for entity_str in entity_strings:
                # Look for name patterns
                name_patterns = [
                    r'(?:^|[|]\s*)name:([^|]+?)(?:\s*[|]|$)',
                    r'(?:^|[|]\s*)inv_name:([^|]+?)(?:\s*[|]|$)'
                ]
                
                for pattern in name_patterns:
                    matches = re.findall(pattern, entity_str)
                    for match in matches:
                        name = match.strip()
                        if name and name != "n/a":
                            names.add(name)
            
            if names:
                sorted_names = sorted(names)
                response = f"Here are all the interface names ({len(sorted_names)} total):\n\n"
                for i, name in enumerate(sorted_names, 1):
                    response += f"{i:4d}. {name}\n"
                    # Limit display to avoid overwhelming
                    if i >= 100:
                        response += f"\n... and {len(sorted_names) - 100} more interfaces.\n"
                        break
                
                if len(sorted_names) > 100:
                    response += f"\n💡 **Total found**: {len(sorted_names)} interfaces"
                
                return response
        
        # Fallback: try to extract from raw response
        raw_response = cache.get('raw_response', {})
        if isinstance(raw_response, dict) and 'data' in raw_response:
            data = raw_response['data']
            if isinstance(data, list):
                names = []
                for item in data:
                    if isinstance(item, dict) and 'name' in item:
                        names.append(item['name'])
                
                if names:
                    response = f"Here are the interface names ({len(names)} total):\n\n"
                    for i, name in enumerate(names, 1):
                        response += f"{i:4d}. {name}\n"
                        if i >= 100:
                            response += f"\n... and {len(names) - 100} more interfaces.\n"
                            break
                    return response
        
        # Final fallback: use cached summary but mention it's not a complete list
        return f"Based on the cached analysis, here's what I found:\n\n{cache.get('processed_summary', 'No detailed interface list available in cache.')}\n\n💡 **Note**: This is a summary. For a complete list of interface names, please clear the cache and ask again to get fresh data."
        
    except Exception as e:
        return f"Error generating list response: {str(e)}\n\nFallback summary:\n{cache.get('processed_summary', 'No analysis available')}"

def generate_count_response(cache: Dict[str, Any], user_question: str) -> str:
    """Generate a count response from cached data"""
    try:
        # Try to get count from raw response summary
        raw_summary = cache.get('raw_response_summary', {})
        if 'total_items' in raw_summary:
            total = raw_summary['total_items']
            return f"**Total count**: {total:,} interfaces found.\n\n{cache.get('processed_summary', '')}"
        
        # Try to count from entity strings
        entity_strings = cache.get('entity_strings', [])
        if entity_strings:
            return f"**Total count**: {len(entity_strings):,} interfaces found based on cached entity data.\n\n{cache.get('processed_summary', '')}"
        
        # Fallback to summary
        return f"Count information from cached analysis:\n\n{cache.get('processed_summary', 'No count information available in cache.')}"
        
    except Exception as e:
        return f"Error generating count response: {str(e)}\n\nFallback:\n{cache.get('processed_summary', 'No analysis available')}"

def generate_search_response(cache: Dict[str, Any], user_question: str) -> str:
    """Generate a search response from cached data"""
    try:
        # Extract search terms from question
        question_lower = user_question.lower()
        search_terms = []
        
        # Simple search term extraction
        if 'find' in question_lower:
            parts = question_lower.split('find')
            if len(parts) > 1:
                search_terms.append(parts[1].strip())
        
        if 'search' in question_lower:
            parts = question_lower.split('search')
            if len(parts) > 1:
                search_terms.append(parts[1].strip())
        
        # Try to search in entity strings
        entity_strings = cache.get('entity_strings', [])
        if entity_strings and search_terms:
            matches = []
            for entity_str in entity_strings:
                entity_lower = entity_str.lower()
                for term in search_terms:
                    if term in entity_lower:
                        matches.append(entity_str)
                        break
            
            if matches:
                response = f"Found {len(matches)} matching interfaces:\n\n"
                for i, match in enumerate(matches[:20], 1):  # Limit to first 20
                    # Extract name from entity string
                    import re
                    name_match = re.search(r'(?:^|[|]\s*)(?:inv_)?name:([^|]+?)(?:\s*[|]|$)', match)
                    if name_match:
                        name = name_match.group(1).strip()
                        response += f"{i:2d}. {name}\n"
                    else:
                        response += f"{i:2d}. {match[:60]}...\n"
                
                if len(matches) > 20:
                    response += f"\n... and {len(matches) - 20} more matches.\n"
                
                return response
        
        # Fallback to cached summary
        return f"Search results from cached analysis:\n\n{cache.get('processed_summary', 'No search results available in cache.')}"
        
    except Exception as e:
        return f"Error generating search response: {str(e)}\n\nFallback:\n{cache.get('processed_summary', 'No analysis available')}"

def show_method_health():
    """Display method health status"""
    st.markdown("---")
    st.markdown("## 🔧 Method Health Status")
    
    try:
        health_status = st.session_state.method_router.get_health_status()
        
        st.json(health_status)
        
        # Show individual method status
        for method, status in health_status.get("method_status", {}).items():
            if status.get("status") == "healthy":
                st.success(f"✅ {method}: {status.get('status', 'unknown')}")
            elif status.get("status") == "error":
                st.error(f"❌ {method}: {status.get('error', 'unknown error')}")
            else:
                st.info(f"ℹ️ {method}: {status.get('status', 'unknown')}")
                
    except Exception as e:
        st.error(f"Failed to get health status: {str(e)}")

def show_response_logs():
    """Display response logs with statistics"""
    st.markdown("---")
    st.markdown("## 📊 Response Logs & Statistics")
    
    try:
        # Get statistics
        stats = st.session_state.response_logger.get_statistics()
        
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Responses", stats.get("total_logs", 0))
        with col2:
            st.metric("Success", stats.get("success_count", 0))
        with col3:
            st.metric("Errors", stats.get("error_count", 0))
        with col4:
            success_rate = stats.get("success_rate", 0) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Method usage
        st.markdown("### Method Usage")
        method_usage = stats.get("method_usage", {})
        if method_usage:
            st.bar_chart(method_usage)
        else:
            st.info("No method usage data yet")
        
        # Recent logs
        st.markdown("### Recent Responses")
        log_filter = st.selectbox("Filter by status", ["all", "success", "error", "partial"])
        
        if log_filter == "all":
            recent_logs = st.session_state.response_logger.get_recent_logs(limit=10)
        else:
            recent_logs = st.session_state.response_logger.get_recent_logs(limit=10, status=log_filter)
        
        if recent_logs:
            for i, log in enumerate(recent_logs):
                status_icon = "✅" if log["status"] == "success" else "❌" if log["status"] == "error" else "⚠️"
                with st.expander(f"{status_icon} {log['question'][:80]}...", expanded=False):
                    st.markdown(f"**Status:** {log['status']}")
                    st.markdown(f"**Method:** {log['method_used']}")
                    st.markdown(f"**Model:** {log.get('model_used', 'N/A')}")
                    st.markdown(f"**Data Source:** {log.get('data_source', 'N/A')}")
                    st.markdown(f"**Execution Time:** {log.get('execution_time_ms', 0):.2f}ms")
                    st.markdown(f"**Timestamp:** {log['timestamp']}")
                    
                    if log['status'] == 'error':
                        st.error(f"**Error:** {log.get('error_message', 'Unknown error')}")
                    else:
                        st.markdown(f"**Answer:** {log['answer'][:200]}...")
        else:
            st.info("No logs found")
        
        # Export logs
        st.markdown("### Export Logs")
        if st.button("Export Today's Logs"):
            today = datetime.now().strftime("%Y-%m-%d")
            export_file = f"response_logs_export_{today}.jsonl"
            st.session_state.response_logger.export_logs(export_file, date=today)
            st.success(f"Logs exported to {export_file}")
                
    except Exception as e:
        st.error(f"Failed to display response logs: {str(e)}")

def show_saved_results():
    """Display saved results in an expandable section"""
    if hasattr(st.session_state, 'result_saver'):
        results = st.session_state.result_saver.get_all_results()
        stats = st.session_state.result_saver.get_stats()
        
        if results:
            st.markdown("### 💾 Saved Results")
            st.markdown(f"**Total Results:** {stats['total']}")
            
            # Show statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**By Method:**")
                for method, count in stats.get('methods', {}).items():
                    st.text(f"  {method}: {count}")
            
            with col2:
                st.markdown("**By Data Source:**")
                for source, count in stats.get('data_sources', {}).items():
                    st.text(f"  {source}: {count}")
            
            with col3:
                st.markdown("**By Model:**")
                for model, count in stats.get('models', {}).items():
                    st.text(f"  {model}: {count}")
            
            # Show recent results
            st.markdown("**Recent Results:**")
            for result in results[-5:]:  # Show last 5 results
                with st.expander(f"ID {result['id']}: {result['question'][:50]}...", expanded=False):
                    st.markdown(f"**Question:** {result['question']}")
                    st.markdown(f"**Method:** {result['method']}")
                    st.markdown(f"**Model:** {result['model']}")
                    st.markdown(f"**Data Source:** {result['data_source']}")
                    st.markdown(f"**Timestamp:** {result['timestamp']}")
                    st.markdown("**Answer:**")
                    st.markdown(result['answer'][:500] + "..." if len(result['answer']) > 500 else result['answer'])
                    
                    if result.get('metadata'):
                        with st.expander("Metadata", expanded=False):
                            st.json(result['metadata'])
        else:
            st.info("No saved results yet. Results will be saved automatically after each query.")
    else:
        st.warning("Result saver not initialized.")

def chat_page():
    """Display main chat interface"""
    st.title("🔍 WHINT API AI Assistant")
    
    # Data Source Selector
    with st.expander("Data Source", expanded=False):
        source = st.radio("Select data source", ["API", "Local JSON File", "Local Engine (DuckDB)", "Neo4j Graph", "Browser Automation"], index=0)
        local_file = ""
        duckdb_path = ""
        
        # Browser Automation Settings
        if source == "Browser Automation":
            st.info("🌐 Browser Automation: AI-powered web navigation and data extraction")
            st.markdown("**Perfect for:** Interacting with WHINT dashboard, extracting data from web pages")
            st.markdown("**Note:** This will open a visible browser window (for testing)")
            
            # Get available models dynamically (same as main sidebar)
            available_models_dict = st.session_state.llm_manager.get_available_models(show_all=True)
            available_model_names = list(available_models_dict.keys())
            
            # Add local Ollama models
            try:
                ollama_models_local = get_local_ollama_models()
                for ollama_model in ollama_models_local:
                    if ollama_model not in available_model_names:
                        available_model_names.append(ollama_model)
            except:
                pass
            
            # Add "None" for fallback
            fallback_model_options = available_model_names + ["None"]
            
            with st.form("browser_config_form"):
                col1, col2 = st.columns(2)
                with col1:
                    browser_username = st.text_input("Microsoft Username", value="", placeholder="user@company.com", help="Microsoft login credentials")
                    browser_primary_model = st.selectbox(
                        "Primary Model",
                        available_model_names,
                        index=0 if len(available_model_names) > 0 else 0,
                        help="Select any available model"
                    )
                with col2:
                    browser_password = st.text_input("Microsoft Password", value="", type="password", help="Microsoft password")
                    browser_fallback_model_raw = st.selectbox(
                        "Fallback Model",
                        fallback_model_options,
                        index=1 if len(fallback_model_options) > 1 else 0,
                        help="Backup model if primary fails"
                    )
                    browser_fallback_model = None if browser_fallback_model_raw == "None" else browser_fallback_model_raw
                
                browser_whint_url = st.text_input("WHINT URL", value="https://whintic-test.cfapps.eu10.hana.ondemand.com/")
                browser_headless = st.checkbox("Headless mode (hidden browser)", value=False)
                
                submitted = st.form_submit_button("💾 Save Browser Settings")
                if submitted:
                    st.session_state.browser_settings_saved = {
                        "username": browser_username,
                        "password": browser_password,
                        "whint_url": browser_whint_url,
                        "primary_model": browser_primary_model,
                        "fallback_model": browser_fallback_model,
                        "headless": browser_headless
                    }
                    st.success("✅ Browser automation settings saved!")
            
            # Show example queries
            with st.expander("💡 Example Browser Automation Queries", expanded=False):
                st.markdown("""
                **Dashboard Queries:**
                - "Navigate to Objects and count how many interfaces are listed"
                - "Go to the dashboard and tell me the system status"
                - "Click Analyze on the first object and summarize findings"
                - "Find the most recent interface and extract its details"
                - "Navigate to Reports and extract the summary statistics"
                
                **Note:** Make sure to click 'Save Browser Settings' before asking questions.
                """)
        
        elif source == "Local JSON File":
            default_local = str(Path("23-09-2025.json").resolve())
            local_file = st.text_input("Local JSON path", value=default_local, help="Path to large JSON file to query")
        elif source == "Local Engine (DuckDB)":
            default_duckdb = str(Path("duckdb_engine/wic.duckdb").resolve())
            duckdb_path = st.text_input("DuckDB database path", value=default_duckdb, help="Path to DuckDB database file")
            st.info("🚀 DuckDB Engine execution, no caching")
        elif source == "Neo4j Graph":
            st.info("🕸️ Neo4j Graph: Relationship analysis using graph database")
            st.markdown("**Perfect for:** Finding connections, paths, and relationships between systems")
            st.markdown("**Neo4j Configuration:**")
            col1, col2 = st.columns(2)
            with col1:
                neo4j_uri = st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j connection URI")
                neo4j_user = st.text_input("Neo4j User", value=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
            with col2:
                neo4j_password = st.text_input("Neo4j Password", value=os.getenv("NEO4J_PASSWORD", ""), type="password", help="Neo4j password")
            
            # Test Neo4j connection
            if st.button("Test Neo4j Connection", key="test_neo4j"):
                try:
                    from src.graph_store_neo4j import Neo4jGraphStore
                    store = Neo4jGraphStore(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
                    result = store.run_tx("MATCH (n) RETURN count(n) as total")
                    total_nodes = result[0]['total'] if result else 0
                    store.close()
                    st.success(f"✅ Connected to Neo4j! Found {total_nodes} nodes.")
                except Exception as e:
                    st.error(f"❌ Neo4j connection failed: {str(e)}")
                    st.info("💡 Make sure Neo4j is running and credentials are correct.")
            
            # Show example queries for Neo4j
            with st.expander("💡 Example Neo4j Graph Queries", expanded=False):
                st.markdown("""
                **Relationship Queries:**
                - "Show all systems connected to Salesforce"
                - "What is the path from SAP to Azure?"
                - "Find all interfaces that connect to MuleSoft"
                - "Show the data flow between System A and System B"
                - "What systems are 2 hops away from SAP?"
                
                **Note:** These queries only work when Neo4j Graph is selected as the data source.
                """)
        
        # Live Data Sync Section (for all sources)
        st.markdown("---")
        st.markdown("### 🔄 Live Data Sync")
        st.markdown("Fetch live data from API and update all storage systems")
        
        with st.expander("Sync Options", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                sync_to_json = st.checkbox("Update JSON file", value=True, help="Save to timestamped JSON file")
                sync_to_duckdb = st.checkbox("Update DuckDB", value=True, help="Update DuckDB database")
            with col2:
                sync_to_neo4j = st.checkbox("Update Neo4j", value=False, help="Update Neo4j graph database")
                sync_max_records = st.number_input("Max records (0 = all)", min_value=0, max_value=100000, value=0, step=1000, help="Limit for testing (0 = fetch all)")
            
            if st.button("🚀 Start Live Sync", type="primary", key="start_live_sync"):
                try:
                    from live_data_sync import LiveDataSync
                    
                    with st.spinner("🔄 Syncing live data..."):
                        # Create progress display
                        progress_text = st.empty()
                        progress_bar = st.progress(0)
                        
                        # Initialize syncer
                        progress_text.text("📡 Connecting to WHINT API...")
                        progress_bar.progress(10)
                        
                        syncer = LiveDataSync()
                        
                        # Fetch data
                        progress_text.text("📥 Fetching live data from API...")
                        progress_bar.progress(20)
                        
                        max_recs = sync_max_records if sync_max_records > 0 else None
                        data = syncer.fetch_live_data(max_records=max_recs)
                        
                        if not data:
                            st.error("❌ No data fetched from API")
                        else:
                            progress_bar.progress(40)
                            
                            # Save to JSON
                            json_file = None
                            if sync_to_json:
                                progress_text.text("💾 Saving to JSON...")
                                json_file = syncer.save_to_json(data)
                                progress_bar.progress(50)
                            else:
                                # Save to temp file for other syncs
                                import tempfile
                                temp_fd, json_file = tempfile.mkstemp(suffix='.json', prefix='sync_')
                                with os.fdopen(temp_fd, 'w') as f:
                                    json.dump(data, f)
                                progress_bar.progress(50)
                            
                            # Update DuckDB
                            if sync_to_duckdb and json_file:
                                progress_text.text("🦆 Updating DuckDB...")
                                duckdb_success = syncer.update_duckdb(json_file)
                                progress_bar.progress(70)
                            
                            # Update Neo4j
                            if sync_to_neo4j and json_file:
                                progress_text.text("🕸️  Updating Neo4j...")
                                neo4j_success = syncer.update_neo4j(json_file)
                                progress_bar.progress(90)
                            
                            # Cleanup temp file if used
                            if not sync_to_json and json_file and os.path.exists(json_file):
                                os.remove(json_file)
                            
                            progress_bar.progress(100)
                            progress_text.text("✅ Sync completed!")
                            
                            # Show results
                            st.success(f"✅ Successfully synced {len(data)} records!")
                            
                            with st.expander("📊 Sync Summary", expanded=True):
                                st.markdown(f"**Records Fetched:** {len(data)}")
                                st.markdown(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                if sync_to_json and json_file:
                                    st.markdown(f"**JSON File:** `{json_file}`")
                                if sync_to_duckdb:
                                    st.markdown(f"**DuckDB:** {'✅ Updated' if 'duckdb_success' in locals() and duckdb_success else '⏭️  Skipped'}")
                                if sync_to_neo4j:
                                    st.markdown(f"**Neo4j:** {'✅ Updated' if 'neo4j_success' in locals() and neo4j_success else '⏭️  Skipped'}")
                            
                            st.info("💡 Tip: Now you can query the updated data using any data source!")
                
                except ImportError:
                    st.error("❌ Live Data Sync module not found. Make sure `live_data_sync.py` exists.")
                except Exception as e:
                    st.error(f"❌ Sync failed: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())

    # Sidebar with connection info
    with st.sidebar:
        st.markdown("### Connection Status")
        st.success("✅ Connected")
        
        # Method health check
        if st.button("🔧 Check Method Health"):
            show_method_health()
        
        # Response logs
        if st.button("📊 View Response Logs"):
            show_response_logs()
        
        if st.button("💾 View Saved Results"):
            show_saved_results()
        
        # Show current connection details
        creds = st.session_state.get('credentials', {})
        storage_source = st.session_state.get('credential_source', 'Session Only')
        
        if creds:
            st.markdown("**Current Connection:**")
            st.text(f"API: {creds.get('api_url', 'N/A')}")
            st.text(f"User: {creds.get('username', 'N/A')}")
            # Show selected provider and API key status
            if 'selected_model' in st.session_state and st.session_state.selected_model:
                selected_model = st.session_state.selected_model
                available_models = st.session_state.llm_manager.get_available_models(show_all=True)
                
                # Always determine provider dynamically for better accuracy
                def get_provider_from_model_name(model_name):
                    """Determine provider from model name"""
                    model_lower = model_name.lower()
                    if 'gemini' in model_lower:
                        return "Google"
                    elif 'gpt' in model_lower or 'openai' in model_lower:
                        return "OpenAI"
                    elif 'claude' in model_lower:
                        return "Anthropic"
                    elif 'groq' in model_lower:
                        return "Groq"
                    elif 'ollama' in model_lower or any(x in model_lower for x in ['llama', 'mistral', 'qwen', 'granite', 'deepseek', 'kimi']):
                        return "Ollama"
                    else:
                        return "Unknown"
                
                # Check if model exists in available_models
                if selected_model in available_models:
                    model_info = available_models[selected_model]
                    provider = model_info.provider.value
                    key_env = model_info.api_key_env
                    key_present = bool(os.getenv(key_env)) or bool(creds.get(f"{provider.lower()}_key"))
                    st.text(f"{provider.capitalize()}: {'✓' if key_present else '✗'}")
                else:
                    # Handle dynamic models - use dynamic provider detection
                    provider = get_provider_from_model_name(selected_model)
                    # Check if it's a local model (Ollama) or cloud model
                    if provider == "Ollama":
                        st.text(f"{provider}: ✓ (Local model)")
                    else:
                        st.text(f"{provider}: ✓ (Cloud model)")
            else:
                st.text("No model selected")
            st.text(f"Storage: {storage_source}")
        
        st.markdown("---")
        
        # Vector Store Statistics
        try:
            stats = st.session_state.vector_store.get_collection_stats()
            st.markdown("**Vector Knowledge Base:**")
            st.text(f"DuckDB Q&A: {stats.get('duckdb_qa_pairs', 0)}")
            st.text(f"API Q&A: {stats.get('api_qa_pairs', 0)}")
            st.text(f"Total: {stats.get('total_qa_pairs', 0)}")
        except Exception as e:
            st.text(f"Vector Store: Error")
        
        st.markdown("---")
        
        # Vector Store Exploration
        st.markdown("**Knowledge Base:**")
        if st.button("📚 Explore Q&A Pairs", key="explore_qa"):
            st.session_state.show_qa_explorer = True
        
        if st.button("🔍 Find Similar Questions", key="find_similar"):
            st.session_state.show_similarity_search = True
        
        st.markdown("---")
        
        # Credential management options
        st.markdown("**Credential Management:**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update", key="update_creds"):
                st.session_state.authenticated = False
                st.rerun()
        with col2:
            if st.button("Disconnect", key="disconnect"):
                st.session_state.authenticated = False
                st.session_state.credentials = {}
                st.session_state.chat_history = []
                st.rerun()
        
        st.markdown("---")
        
        # System Prompts Section
        with st.expander("📝 System Prompts", expanded=False):
            st.markdown("**Translation Prompt:**")
            translation_prompt = build_system_prompt_translation(
                include_examples=True,
                sample_interface_count=8
            )
            with st.expander("View Translation Prompt", expanded=False):
                st.text(translation_prompt)
            
            st.markdown("**Synthesis Prompt:**")
            synthesis_prompt = build_system_prompt_synthesis()
            with st.expander("View Synthesis Prompt", expanded=False):
                st.text(synthesis_prompt)
        
        st.markdown("---")
        
        # Cache Statistics Section
        with st.expander("📊 Cache Statistics", expanded=False):
            cache_stats = st.session_state.knowledge_store.get_cache_stats()
            
            st.metric("Total Entries", cache_stats['total_entries'])
            st.metric("Valid Entries", cache_stats['valid_entries'])
            st.metric("Expired Entries", cache_stats['expired_entries'])
            st.metric("Total Items Cached", cache_stats['total_items_cached'])
            st.metric("Cache Size (MB)", cache_stats['cache_size_mb'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Cleanup Expired", help="Remove expired cache entries"):
                    cleaned = st.session_state.knowledge_store.cleanup_expired()
                    st.success(f"Cleaned up {cleaned} expired entries!")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Refresh Stats", help="Refresh cache statistics"):
                    st.rerun()
            
            # Cache Search
            st.markdown("**🔍 Search Cache:**")
            search_term = st.text_input("Search cached responses", placeholder="Enter keywords...")
            if search_term:
                search_results = st.session_state.knowledge_store.search_cache(search_term)
                if search_results:
                    st.write(f"Found {len(search_results)} matching entries:")
                    for result in search_results[:3]:  # Show first 3 results
                        with st.expander(f"📄 {result['summary_preview'][:50]}..."):
                            st.write(f"**Endpoint:** {result['endpoint']}")
                            st.write(f"**Created:** {result['created_at']}")
                            st.write(f"**Items:** {result['total_items']}")
                            st.write(f"**Preview:** {result['summary_preview']}")
                else:
                    st.info("No matching cached responses found.")
            
            # Cache Management
            st.markdown("**⚙️ Cache Management:**")
            if st.button("📋 View All Cached Entries", help="View all cached responses"):
                all_entries = []
                for cache_key, entry in st.session_state.knowledge_store.index.items():
                    if st.session_state.knowledge_store._is_cache_valid(entry):
                        all_entries.append({
                            'key': cache_key,
                            'endpoint': entry.get('endpoint', 'Unknown'),
                            'created': entry.get('created_at', 'Unknown'),
                            'items': entry.get('total_items', 0),
                            'preview': entry.get('summary_preview', 'No preview')[:100]
                        })
                
                if all_entries:
                    st.write(f"**Found {len(all_entries)} valid cached entries:**")
                    for entry in all_entries:
                        with st.expander(f"🔑 {entry['key'][:8]}... - {entry['items']} items"):
                            st.write(f"**Endpoint:** {entry['endpoint']}")
                            st.write(f"**Created:** {entry['created']}")
                            st.write(f"**Items:** {entry['items']}")
                            st.write(f"**Preview:** {entry['preview']}")
                else:
                    st.info("No valid cached entries found.")
        
        st.markdown("---")
        # LLM Model Selection
        available_models = st.session_state.llm_manager.get_available_models(show_all=True)
        model_names = list(available_models.keys())

        # Include local Ollama models in dropdown even if not in config
        try:
            local_ollama_models = get_local_ollama_models()
        except Exception:
            local_ollama_models = []
        
        # Add dynamic Ollama models to available_models dictionary
        from src.llm_providers import ModelConfig, LLMProvider
        for ollama_model_name in local_ollama_models:
            if ollama_model_name not in available_models:
                available_models[ollama_model_name] = ModelConfig(
                    name=ollama_model_name,
                    provider=LLMProvider.OLLAMA,
                    context_length=0,  # Unknown, or fetch dynamically if possible
                    cost_per_1k_tokens=0.0,
                    supports_json=True,  # Assume for now
                    supports_images=False,  # Assume for now
                    api_key_env="OLLAMA_BASE_URL",
                    description=f"Local Ollama model: {ollama_model_name}"
                )
        
        model_names = list(available_models.keys())
        full_model_list = model_names

        if full_model_list:
            default_index = full_model_list.index(st.session_state.selected_model) if st.session_state.selected_model in full_model_list else 0
            selected_model = st.selectbox(
                "Select LLM Model",
                full_model_list,
                index=default_index,
                key="llm_model_select"
            )
            # Check if model actually changed
            if st.session_state.selected_model != selected_model:
                st.session_state.selected_model = selected_model
                # Force refresh to update sidebar immediately
                st.rerun()
            
            # Show model info (all models are now in available_models)
            model_info = available_models[selected_model]
            st.markdown(f"**Model:** {model_info.name}")
            st.markdown(f"**Provider:** {model_info.provider.value}")
            st.markdown(f"**Context Length:** {model_info.context_length}")
            # Show API key status where applicable
            has_key = st.session_state.llm_manager.check_api_key_for_model(selected_model)
            if model_info.provider.value.lower() == "ollama":
                st.success("Local Ollama model selected (no API key required).")
            elif has_key:
                st.success("API key found for this model.")
            else:
                st.warning(f"No API key found for {model_info.provider.value}. Add it in credentials to use this model.")
        else:
            st.warning("No LLM models available. Please check your API keys or Ollama installation.")
    
    st.markdown("---")
    
    # Chat history
    if st.session_state.chat_history:
        st.markdown("### Previous Questions")
        for i, chat in enumerate(st.session_state.chat_history):
            with st.expander(f"Q: {chat['question'][:50]}...", expanded=False):
                st.markdown(f"**Question:** {chat['question']}")
                st.markdown(f"**Answer:** {chat['answer']}")
    
    # Main question input
    st.markdown("### Ask Your Question")

    # Example presets for quick selection - organized by category
    presets = [
        "— None —",
        
        # ═══════════════════════════════════════════════════════════
        # 📊 TYPE-BASED QUERIES (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "📊 Show APIM interfaces",
        "📊 List SAP interfaces",
        "📊 Find SAP IDOC interfaces",
        "📊 Show SAP ODATA interfaces",
        "📊 List SAP Process Orchestration (PO) interfaces",
        "📊 Show SAP EventMesh interfaces",
        "📊 List MuleSoft applications",
        "📊 Find Azure interfaces",
        "📊 Show all EAM interfaces",
        
        # ═══════════════════════════════════════════════════════════
        # 🔍 NAME & TEXT SEARCH (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "🔍 Show interfaces where name contains 'Connect'",
        "🔍 Find interfaces with 'Business Partner' in name",
        "🔍 List interfaces containing 'EXCHANGE_RATE'",
        "🔍 Show interfaces starting with 'AGS_'",
        "🔍 Find all Salesforce interfaces",
        
        # ═══════════════════════════════════════════════════════════
        # 🔗 SENDER & RECEIVER QUERIES (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "🔗 Find interfaces from SAP Solution Manager",
        "🔗 Show interfaces to Workday HCM",
        "🔗 List interfaces from SAP S/4HANA",
        "🔗 Find interfaces with sender 'Enterprise Alert'",
        "🔗 Show interfaces where receiver is 'B2B Supplier'",
        "🔗 Find interfaces with no sender",
        "🔗 Show interfaces with no receiver",
        
        # ═══════════════════════════════════════════════════════════
        # 📈 ANALYTICAL QUERIES (DuckDB)
        # ═══════════════════════════════════════════════════════════
        "📈 Show all interfaces (complete dataset)",
        "📈 Count interfaces by type",
        "📈 Show top 10 most common senders",
        "📈 Find interfaces with missing descriptions",
        "📈 List first 50 interfaces alphabetically",
        
        # ═══════════════════════════════════════════════════════════
        # 🏷️ METADATA & PROPERTIES (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "🏷️ Get interfaces with metadata included",
        "🏷️ Show interfaces with properties",
        "🏷️ List interfaces with tags",
        "🏷️ Find interfaces with all objects included",
        
        # ═══════════════════════════════════════════════════════════
        # 🌐 BUSINESS SCENARIOS (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "🌐 Show currency exchange rate interfaces",
        "🌐 Find business partner replication flows",
        "🌐 List all OANDA integrations",
        "🌐 Show European Central Bank interfaces",
        "🌐 Find marketing cloud integrations",
        
        # ═══════════════════════════════════════════════════════════
        # 🚫 EXCLUSION QUERIES (DuckDB/API)
        # ═══════════════════════════════════════════════════════════
        "🚫 Exclude EAM and PLANNED interfaces",
        "🚫 Show interfaces that are NOT type 21",
        "🚫 List non-SAP interfaces",
        
        # ═══════════════════════════════════════════════════════════
        # 🕸️ GRAPH QUERIES (Neo4j Only)
        # ═══════════════════════════════════════════════════════════
        "🕸️ Show all systems connected to Salesforce",
        "🕸️ What is the path from SAP to Azure?",
        "🕸️ Find all interfaces that connect to MuleSoft",
        "🕸️ Show the data flow between System A and System B",
        "🕸️ What systems are 2 hops away from SAP?",
        "🕸️ Find shortest path from SharePoint to SAP",
        
        # ═══════════════════════════════════════════════════════════
        # 📋 OTHER ENTITIES (API)
        # ═══════════════════════════════════════════════════════════
        "📋 List all tasks with failed runs",
        "📋 Show all log entries",
        "📋 List all datasources",
        "📋 Find systems containing 'SAP'",
        "📋 Show dataflows containing 'sync'",
    ]
    preset = st.selectbox("Example Presets", presets, index=0, help="Select to prefill a query example")

    default_question = ""
    if preset and preset != "— None —":
        # Remove emoji prefix (e.g., "📊 " from "📊 Show APIM interfaces")
        default_question = preset.split(' ', 1)[1] if ' ' in preset else preset

    user_question = st.text_area(
        "What would you like to know about your integration landscape?",
        value=default_question,
        placeholder="Example: Show me all MULE APIs that are currently active...",
        height=100
    )
    
    if st.button("Ask AI Assistant", type="primary"):
        if user_question.strip():
            selected_model = st.session_state.selected_model
            has_key = st.session_state.llm_manager.check_api_key_for_model(selected_model)
            if not has_key:
                # Get model info to check if it's Ollama
                model_info = st.session_state.llm_manager.models.get(selected_model)
                if model_info and model_info.provider.value.lower() == "ollama":
                    st.error("Ollama service is not accessible. Please make sure Ollama is running on localhost:11434")
                else:
                    st.error(f"No API key found for the selected model's provider. Please add the API key in your credentials to use this model.")
                return
            with st.spinner("Processing your question..."):
                # Step 1: Determine data source type for routing
                # Map source selection to routing data source types
                if source == "Local JSON File":
                    data_source_type = "local_json"
                elif source == "Local Engine (DuckDB)":
                    data_source_type = "duckdb"
                elif source == "Neo4j Graph":
                    data_source_type = "neo4j"
                elif source == "Browser Automation":
                    data_source_type = "browser_automation"
                else:  # API
                    data_source_type = "api"
                
                # SPECIAL HANDLING FOR API MODE: Skip routing, use direct API fetch
                # This preserves the original simple behavior: fetch live data → chunk → analyze
                if source == "API":
                    st.info("📡 Fetching live data from WHINT API...")
                    
                    # Create API query
                    api_query = create_api_query(user_question, selected_model)
                    api_endpoint = determine_api_endpoint(api_query, st.session_state.credentials['api_url'])
                    
                    if api_query:
                        start_time = datetime.now()
                        
                        # Execute live API call
                        api_response = execute_api_query(api_query, st.session_state.credentials)
                        if api_response:
                            # Analyze with chunking mechanism (handles large responses)
                            analysis = analyze_response(user_question, api_response, st.session_state.credentials['openai_key'])
                            
                            execution_time = (datetime.now() - start_time).total_seconds() * 1000
                            
                            # Store Q&A pair in vector database
                            try:
                                intent = analyze_user_intent(user_question)
                                
                                qa_id = st.session_state.vector_store.store_qa_pair(
                                    question=user_question,
                                    answer=analysis,
                                    query=api_query,
                                    endpoint=api_endpoint,
                                    intent=intent,
                                    data_source="api",
                                    response_data=api_response,
                                    method="api_direct"
                                )
                                
                                if qa_id:
                                    st.success(f"✅ Fetched live data and stored in vector database (ID: {qa_id[:8]}...)")
                            except Exception as e:
                                st.warning(f"⚠️ Data fetched but storage failed: {str(e)}")
                            
                            # Log the response
                            try:
                                st.session_state.response_logger.log_response(
                                    question=user_question,
                                    answer=analysis,
                                    status="success",
                                    method_used="api_direct",
                                    model_used=selected_model,
                                    data_source="api",
                                    intent=intent,
                                    api_query=api_query,
                                    endpoint=api_endpoint,
                                    response_data=api_response,
                                    execution_time_ms=execution_time
                                )
                            except Exception as e:
                                pass  # Non-fatal
                            
                            st.markdown("### Answer (from Live API)")
                            st.markdown(analysis)
                            
                            with st.expander("📊 Response Details", expanded=False):
                                st.markdown(f"**⏱️ Execution Time:** {execution_time:.0f}ms")
                                st.markdown(f"**🔗 API Endpoint:** `{api_endpoint}`")
                                
                                # Show data summary
                                if isinstance(api_response, dict) and 'data' in api_response:
                                    data_count = len(api_response.get('data', []))
                                    st.markdown(f"**📊 Records Returned:** {data_count}")
                                    st.markdown(f"**💾 Storage:** Vector database (ChromaDB)")
                                    st.markdown(f"**📝 Log:** `response_logs/daily/responses_{datetime.now().strftime('%Y-%m-%d')}.jsonl`")
                                    
                                    if data_count > 0:
                                        st.markdown("**Sample (first 3 records):**")
                                        st.json(api_response['data'][:3])
                                else:
                                    st.json(api_response)
                            
                            with st.expander("🔧 Technical Details", expanded=False):
                                st.markdown("**Generated API Query:**")
                                st.json(api_query)
                                st.markdown("**Full API Response:**")
                                st.json(api_response)
                        else:
                            st.error("Failed to fetch data from API.")
                    else:
                        st.error("Failed to create API query from your question.")
                    
                    return  # Exit early for API mode
                
                # Step 2: Route query to appropriate method based on data source
                # (Only for non-API sources: Local JSON, DuckDB, Neo4j, Browser)
                st.info(f"🔍 Analyzing your question and routing to best method for {data_source_type}...")
                
                # Initialize method router
                method_router = MethodRouter(st.session_state.credentials.get('openai_key', ''))
                
                # Route the query with data source awareness
                routing_result = method_router.route_query(user_question, data_source=data_source_type)
                method_name = routing_result["method_name"]
                method_params = routing_result["method_params"]
                routing_info = routing_result["routing_info"]
                
                # Show routing information
                with st.expander("🔀 Query Routing", expanded=False):
                    st.json({
                        "data_source": data_source_type,
                        "selected_method": method_name,
                        "routing_logic": {
                            "local_json": "→ vector_rag (simple vector search)",
                            "duckdb": "→ db_lookup (direct SQL queries)",
                            "neo4j": "→ graph_rag (graph relationships)",
                            "api": "→ intent-based routing"
                        },
                        "requires_graph": routing_info["intent"].get("requires_graph", False),
                        "query_type": routing_info["intent"].get("query_type", "api"),
                        "graph_seeds": routing_info["intent"].get("graph_seeds", []),
                        "enabled_methods": routing_info["enabled_methods"]
                    })
                
                # Handle browser_automation method
                if method_name == "browser_automation":
                    st.info("🌐 Using Browser Automation for web interaction...")
                    
                    # Check if browser settings are saved
                    if 'browser_settings_saved' not in st.session_state:
                        st.error("❌ Please configure Browser Automation settings in the Data Source section first!")
                        return
                    
                    browser_settings = st.session_state.browser_settings_saved
                    
                    if not browser_settings.get('username') or not browser_settings.get('password'):
                        st.error("❌ Please provide Microsoft credentials in Browser Automation settings!")
                        return
                    
                    start_time = datetime.now()
                    try:
                        from methods.browser_automation import BrowserAutomationEngine
                        import asyncio
                        
                        # Create browser engine
                        engine = BrowserAutomationEngine(
                            primary_model=browser_settings.get('primary_model', 'gemini-2.0-flash-exp'),
                            fallback_model=browser_settings.get('fallback_model', 'gpt-4o-mini'),
                            headless=browser_settings.get('headless', False),
                            whint_url=browser_settings.get('whint_url', 'https://whintic-test.cfapps.eu10.hana.ondemand.com/'),
                            auto_login=True,
                            username=browser_settings['username'],
                            password=browser_settings['password']
                        )
                        
                        # Run async task
                        async def run_browser_task():
                            try:
                                # Initialize browser
                                init_result = await engine.initialize_browser()
                                if init_result["status"] != "initialized":
                                    return {"status": "error", "error": f"Browser initialization failed: {init_result.get('error')}"}
                                
                                # Execute task
                                result = await engine.execute_task(user_question)
                                
                                # Close browser
                                await engine.close()
                                
                                return result
                            except Exception as e:
                                await engine.close()
                                raise e
                        
                        # Execute with proper event loop (Windows needs ProactorEventLoop for subprocess)
                        import sys
                        import platform
                        
                        if platform.system() == 'Windows':
                            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                        
                        # Get or create event loop
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        result = loop.run_until_complete(run_browser_task())
                        
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        
                        if result["status"] == "success":
                            # Show success response
                            st.success(f"✅ Browser automation completed in {execution_time/1000:.1f}s")
                            
                            with st.expander("🌐 Browser Automation Details", expanded=False):
                                st.markdown(f"**Model Used:** {browser_settings['primary_model']}")
                                st.markdown(f"**Duration:** {result.get('duration_seconds', 0):.1f}s")
                                st.markdown(f"**Auto-Login:** ✅ Success")
                            
                            # Display result
                            st.markdown("### 📊 Result")
                            st.markdown(result["result"])
                            
                            # Log response
                            st.session_state.response_logger.log_response(
                                question=user_question,
                                answer=result["result"],
                                status="success",
                                method_used="browser_automation",
                                model_used=browser_settings['primary_model'],
                                data_source="browser_automation",
                                intent="web_interaction",
                                execution_time_ms=execution_time,
                                metadata={
                                    "whint_url": browser_settings['whint_url'],
                                    "headless": browser_settings['headless']
                                }
                            )
                            
                            # Save result
                            st.session_state.result_saver.save_result(
                                question=user_question,
                                answer=result["result"],
                                method="browser_automation",
                                model=browser_settings['primary_model'],
                                data_source="browser_automation",
                                metadata={
                                    "execution_time_ms": execution_time,
                                    "duration_seconds": result.get("duration_seconds", 0)
                                }
                            )
                        
                        else:
                            st.error(f"❌ Browser automation failed")
                            st.error(result.get("error", "Unknown error"))
                            
                            # Log error
                            st.session_state.response_logger.log_response(
                                question=user_question,
                                answer="",
                                status="error",
                                method_used="browser_automation",
                                model_used=browser_settings['primary_model'],
                                data_source="browser_automation",
                                error_message=result.get("error", "Unknown error"),
                                execution_time_ms=execution_time
                            )
                    
                    except Exception as e:
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        st.error(f"❌ Browser automation error: {str(e)}")
                        
                        # Log error
                        st.session_state.response_logger.log_response(
                            question=user_question,
                            answer="",
                            status="error",
                            method_used="browser_automation",
                            model_used=browser_settings.get('primary_model', 'unknown'),
                            data_source="browser_automation",
                            error_message=str(e),
                            execution_time_ms=execution_time
                        )
                
                # Handle graph_rag method (Neo4j only)
                elif method_name == "graph_rag":
                    st.info("🕸️ Using Graph RAG for Neo4j relationship analysis...")
                    start_time = datetime.now()
                    try:
                        # For Neo4j Graph source, use the provided credentials
                        if source == "Neo4j Graph":
                            # Update environment variables with UI values
                            if 'neo4j_uri' in locals():
                                os.environ['NEO4J_URI'] = neo4j_uri
                            if 'neo4j_user' in locals():
                                os.environ['NEO4J_USER'] = neo4j_user
                            if 'neo4j_password' in locals():
                                os.environ['NEO4J_PASSWORD'] = neo4j_password
                        
                        # Add LLM model and manager to method_params for GraphRAG
                        method_params["llm_model"] = selected_model
                        method_params["llm_manager"] = st.session_state.llm_manager
                        
                        # GraphRAG works directly with Neo4j - no local data needed
                        # It will query Neo4j database for relationships and use LLM for synthesis
                        result, meta = method_router.execute_method(method_name, method_params)
                        
                        # Calculate execution time
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        
                        # Log successful response
                        st.session_state.response_logger.log_response(
                            question=user_question,
                            answer=result,
                            status="success",
                            method_used="graph_rag",
                            model_used=selected_model,
                            data_source="neo4j",
                            intent=routing_info["intent"].get("query_type"),
                            requires_graph=routing_info["intent"].get("requires_graph", False),
                            query_type=routing_info["intent"].get("query_type"),
                            graph_seeds=routing_info["intent"].get("graph_seeds", []),
                            endpoint=meta.get("backend"),
                            execution_time_ms=execution_time,
                            metadata={
                                "backend": meta.get("backend"),
                                "seeds_used": meta.get("seeds", []),
                                "sender_receiver": meta.get("sender_receiver")
                            }
                        )
                        
                        # Save result for future reference
                        st.session_state.result_saver.save_result(
                            question=user_question,
                            answer=result,
                            method="graph_rag",
                            model=selected_model,
                            data_source="neo4j",
                            metadata={
                                "execution_time_ms": execution_time,
                                "seeds_used": meta.get("seeds", []),
                                "neighborhood_count": meta.get("neighborhood_count", 0),
                                "llm_synthesis": meta.get("llm_synthesis", False)
                            }
                        )
                        
                        st.markdown("### Answer (from Neo4j Graph RAG)")
                        st.markdown(result)
                        
                        with st.expander("Graph Analysis Details"):
                            st.json({
                                "method": meta.get("method"),
                                "backend": meta.get("backend"),
                                "seeds_used": meta.get("seeds", []),
                                "sender_receiver": meta.get("sender_receiver"),
                                "execution_time_ms": execution_time
                            })
                        
                        return
                        
                    except Exception as e:
                        # Calculate execution time
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        
                        # Log the error
                        st.session_state.response_logger.log_response(
                            question=user_question,
                            answer="",
                            status="error",
                            method_used="graph_rag",
                            model_used=selected_model,
                            data_source="neo4j",
                            intent=routing_info["intent"].get("query_type"),
                            requires_graph=routing_info["intent"].get("requires_graph", False),
                            execution_time_ms=execution_time,
                            error_message=str(e),
                            error_type=type(e).__name__,
                            error_traceback=traceback.format_exc()
                        )
                        
                        st.error(f"Graph RAG failed: {str(e)}")
                        st.info("💡 Tip: Make sure Neo4j is running and contains data.")
                        return
                
                # Handle vector_rag method (Local JSON with simple RAG)
                if method_name == "vector_rag":
                    st.info("🔍 Using Vector RAG for semantic search...")
                    start_time = datetime.now()
                    try:
                        # Load data for vector search
                        if source == "Local JSON File":
                            try:
                                with open(local_file, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    if isinstance(data, dict) and 'data' in data:
                                        data = data['data']
                            except Exception as e:
                                st.error(f"Failed to load local JSON file: {str(e)}")
                                return
                        else:
                            st.error("Vector RAG is only supported for Local JSON File source.")
                            return
                        
                        # Add LLM model and manager to method_params for VectorRAG
                        method_params["data"] = data
                        method_params["top_k"] = st.session_state.get('vector_rag_top_k', 1000)
                        method_params["similarity_threshold"] = st.session_state.get('vector_rag_similarity_threshold', 0.3)
                        method_params["llm_model"] = selected_model
                        method_params["llm_manager"] = st.session_state.llm_manager
                        
                        # Execute vector_rag with LLM synthesis
                        result, meta = method_router.execute_method(method_name, method_params)
                        
                        # Calculate execution time
                        execution_time = (datetime.now() - start_time).total_seconds() * 1000
                        
                        # Log successful response
                        st.session_state.response_logger.log_response(
                            question=user_question,
                            answer=result,
                            status="success",
                            method_used="vector_rag",
                            model_used=selected_model,
                            data_source="local_json",
                            intent=routing_info["intent"].get("query_type"),
                            execution_time_ms=execution_time,
                            metadata=meta
                        )
                        
                        # Save result for future reference
                        st.session_state.result_saver.save_result(
                            question=user_question,
                            answer=result,
                            method="vector_rag",
                            model=selected_model,
                            data_source="local_json",
                            metadata={
                                "execution_time_ms": execution_time,
                                "retrieved": meta.get("retrieved", 0),
                                "avg_similarity": meta.get("avg_similarity", 0),
                                "llm_synthesis": meta.get("llm_synthesis", False)
                            }
                        )
                        
                        st.markdown("### Answer (from Vector RAG)")
                        st.markdown(result)
                        
                        with st.expander("Vector Search Details"):
                            st.json(meta)
                        
                        return
                        
                    except Exception as e:
                        st.error(f"Vector RAG failed: {str(e)}")
                        return
                
                # Handle db_lookup method (DuckDB with direct SQL)
                if method_name == "db_lookup":
                    st.info("🗄️ Using DuckDB for direct SQL queries...")
                    start_time = datetime.now()
                    # Continue with DuckDB processing below
                    # Don't return yet - let it flow to DuckDB section
                
                # For standard processing (API, DuckDB, or Local JSON fallback)
                # Step 2: Create API query (fallback)
                st.info("🔍 Creating API query...")
                api_query = create_api_query(user_question, st.session_state.selected_model)
                if api_query:
                    with st.expander("Generated API Query", expanded=False):
                        st.json(api_query)
                    api_endpoint = determine_api_endpoint(api_query, st.session_state.credentials['api_url'])
                    
                    # DuckDB mode execution (no cache)
                    if source == "Local Engine (DuckDB)":
                        # Check for similar questions in vector store first
                        try:
                            intent = analyze_user_intent(user_question)
                            similar_qa = st.session_state.vector_store.find_similar_qa(
                                question=user_question,
                                data_source="duckdb",
                                intent=intent,
                                top_k=3
                            )
                            
                            if similar_qa and similar_qa[0]['similarity'] > 0.85:
                                st.info(f"🎯 Found similar question with {similar_qa[0]['similarity']:.1%} similarity!")
                                with st.expander("📚 Similar Question Found", expanded=True):
                                    st.markdown(f"**Similar Question:** {similar_qa[0]['question']}")
                                    st.markdown(f"**Similarity:** {similar_qa[0]['similarity']:.1%}")
                                    st.markdown("**Answer:**")
                                    st.markdown(similar_qa[0]['answer'])
                                    
                                    if st.button("Use This Answer", key="use_similar_answer"):
                                        st.markdown("### Answer (from Similar Question)")
                                        st.markdown(similar_qa[0]['answer'])
                                        return
                                    
                                    if st.button("Continue with DuckDB Query", key="continue_duckdb"):
                                        st.info("🚀 Executing query against DuckDB")
                            else:
                                st.info("🚀 Executing query against DuckDB")
                        except Exception as e:
                            st.warning(f"⚠️ Could not check similar questions: {str(e)}")
                            st.info("🚀 Executing query against DuckDB ")
                        
                        try:
                            start_time = datetime.now()
                            duckdb_executor = DuckDBExecutor(duckdb_path)
                            duckdb_response = duckdb_executor.execute_query(api_query)
                            
                            if duckdb_response and not duckdb_response.get('error'):
                                analysis = analyze_response(user_question, duckdb_response, st.session_state.credentials.get('openai_key', ''))
                                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                                
                                # Store Q&A pair in vector database
                                try:
                                    intent = analyze_user_intent(user_question)
                                    diagnostics = duckdb_executor.get_diagnostics(api_query)
                                    qa_id = st.session_state.vector_store.store_qa_pair(
                                        question=user_question,
                                        answer=analysis,
                                        query=api_query,
                                        endpoint=api_endpoint,
                                        intent=intent,
                                        data_source="duckdb",
                                        response_data=duckdb_response,
                                        sql_query=diagnostics.get('translated_sql')
                                    )
                                    if qa_id:
                                        st.success(f"📚 Q&A pair stored in vector database (ID: {qa_id})")
                                except Exception as e:
                                    st.warning(f"⚠️ Could not store Q&A pair: {str(e)}")
                                
                                # Log the response
                                st.session_state.response_logger.log_response(
                                    question=user_question,
                                    answer=analysis,
                                    status="success",
                                    method_used="duckdb",
                                    model_used=selected_model,
                                    data_source="duckdb",
                                    intent=intent,
                                    api_query=api_query,
                                    endpoint=api_endpoint,
                                    sql_query=diagnostics.get('translated_sql'),
                                    response_data=duckdb_response,
                                    execution_time_ms=execution_time
                                )
                                
                                st.markdown("### Answer (from DuckDB)")
                                st.markdown(analysis)
                                
                                # Show data summary prominently
                                if duckdb_response and 'data' in duckdb_response:
                                    total_items = duckdb_response.get('total', 0)
                                    data_items = duckdb_response.get('data', [])
                                    
                                    st.markdown(f"**📊 Results:** {total_items} interfaces returned")
                                    
                                    # Show first few results in a nice table
                                    if data_items and len(data_items) > 0:
                                        with st.expander(f"📋 View Results ({min(10, len(data_items))} of {total_items} shown)", expanded=False):
                                            import pandas as pd
                                            # Convert first 10 items to DataFrame for nice display
                                            preview_data = data_items[:10]
                                            if preview_data:
                                                df = pd.DataFrame(preview_data)
                                                st.dataframe(df, use_container_width=True)
                                        
                                        # Download option for all data
                                        if total_items > 10:
                                            csv = pd.DataFrame(data_items).to_csv(index=False)
                                            st.download_button(
                                                label=f"⬇️ Download All {total_items} Results as CSV",
                                                data=csv,
                                                file_name=f"sap_interfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                                mime="text/csv"
                                            )
                                
                                with st.expander("Technical Details"):
                                    st.markdown("**Generated API Query:**")
                                    st.json(api_query)
                                    st.markdown("**DuckDB Response:**")
                                    st.json(duckdb_response)
                                    
                                    # Show diagnostics
                                    diagnostics = duckdb_executor.get_diagnostics(api_query)
                                    with st.expander("🔍 DuckDB Diagnostics"):
                                        st.markdown("**Translated SQL:**")
                                        st.code(diagnostics.get('translated_sql', 'N/A'))
                                        st.markdown("**SQL Parameters:**")
                                        st.json(diagnostics.get('sql_params', {}))
                                        st.markdown("**Type Distribution:**")
                                        st.json(diagnostics.get('type_distribution', [])[:10])
                                        st.markdown("**Sample Data:**")
                                        st.json(diagnostics.get('sample_data', [])[:3])
                            else:
                                error_msg = duckdb_response.get('error', 'Unknown error') if duckdb_response else 'No response from DuckDB'
                                st.error(f"DuckDB execution failed: {error_msg}")
                                
                                # Show diagnostics for debugging
                                try:
                                    duckdb_executor = DuckDBExecutor(duckdb_path)
                                    diagnostics = duckdb_executor.get_diagnostics(api_query)
                                    with st.expander("🔍 Debug Information"):
                                        st.markdown("**Database Path:**")
                                        st.text(diagnostics.get('database_path', 'N/A'))
                                        st.markdown("**Database Exists:**")
                                        st.text(diagnostics.get('database_exists', False))
                                        st.markdown("**Translated SQL:**")
                                        st.code(diagnostics.get('translated_sql', 'N/A'))
                                        st.markdown("**SQL Parameters:**")
                                        st.json(diagnostics.get('sql_params', {}))
                                except Exception as diag_error:
                                    st.error(f"Could not get diagnostics: {diag_error}")
                        except Exception as e:
                            st.error(f"DuckDB execution error: {str(e)}")
                        return

                    # Local JSON mode: cache-first (read/write)
                    elif source == "Local JSON File":
                        with st.expander("🔍 Cache Debug Info", expanded=False):
                            st.write("**Generated API Query:**")
                            st.json(api_query)
                            st.write(f"**Endpoint (logical):** {api_endpoint}")
                            cache_key = st.session_state.knowledge_store._generate_cache_key(api_query, api_endpoint)
                            st.write(f"**Generated Cache Key:** `{cache_key}`")
                            cache_stats = st.session_state.knowledge_store.get_cache_stats()
                            st.write("**Cache Statistics:**")
                            st.json(cache_stats)
                        
                        cache = st.session_state.knowledge_store.get_cached_response(api_query, api_endpoint, debug=True)
                        if not cache:
                            st.info("🔍 No exact cache match found. Checking for similar queries...")
                            similar_cache = st.session_state.knowledge_store.get_similar_cached_response(api_query, api_endpoint, similarity_threshold=0.8)
                            if similar_cache:
                                st.success("🎯 Found similar cached response (80%+ similarity)!")
                                cache = similar_cache
                        
                        if cache:
                            user_intent = analyze_user_intent(user_question)
                            if user_intent == "list_all":
                                analysis = generate_list_response(cache, user_question)
                            elif user_intent == "count":
                                analysis = generate_count_response(cache, user_question)
                            elif user_intent == "search":
                                analysis = generate_search_response(cache, user_question)
                            else:
                                analysis = cache.get('processed_summary') or "No analysis available"

                            st.markdown("### Answer (from cache)")
                            st.markdown(analysis)
                            with st.expander("Technical Details"):
                                st.markdown("**Generated API Query:**")
                                st.json(api_query)
                                st.markdown("**API Response:** (from cache)")
                                st.json(cache.get('raw_response_summary', {}))
                            return
                        else:
                            st.info("📄 Executing query against local JSON file...")
                            local_response = execute_query_locally(api_query, api_endpoint, local_file)
                            if local_response:
                                analysis = analyze_response(user_question, local_response, st.session_state.credentials.get('openai_key', ''))
                                st.session_state.knowledge_store.store_response(
                                    query=api_query,
                                    endpoint=api_endpoint,
                                    raw_response=local_response,
                                    processed_summary=analysis,
                                    chunk_summaries=[]
                                )
                                st.markdown("### Answer (from local JSON)")
                                st.markdown(analysis)
                                return
                            else:
                                st.error("Local execution failed. Check file path or content, or switch back to API.")
                                return
                    
                    # Note: API mode is handled earlier (line ~1937) with direct fetch
                    # This section only handles Local JSON and DuckDB
                else:
                    st.error("Failed to create API query from your question.")
        else:
            st.warning("Please enter a question.")
    
    # Q&A Explorer Components
    if st.session_state.get('show_qa_explorer', False):
        show_qa_explorer()
    
    if st.session_state.get('show_similarity_search', False):
        show_similarity_search()

def show_qa_explorer():
    """Display Q&A pairs explorer interface"""
    st.markdown("---")
    st.markdown("## 📚 Q&A Pairs Explorer")
    
    # Data source selection
    data_source = st.selectbox("Data Source", ["duckdb", "api", "local_json"], key="qa_explorer_source")
    
    # Get recent Q&A pairs
    try:
        recent_qa = st.session_state.vector_store.get_recent_qa_pairs(data_source, limit=20)
        
        if recent_qa:
            st.markdown(f"**Recent {data_source.upper()} Q&A Pairs:**")
            
            for i, qa in enumerate(recent_qa):
                with st.expander(f"Q{i+1}: {qa['question'][:80]}...", expanded=False):
                    st.markdown(f"**Question:** {qa['question']}")
                    st.markdown(f"**Answer:** {qa['answer']}")
                    
                    metadata = qa.get('metadata', {})
                    if metadata:
                        st.markdown("**Metadata:**")
                        
                        # Row 1: Method, Strategy, Data Source
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            method = metadata.get('method', 'N/A')
                            st.text(f"🔧 Method: {method}")
                        with col2:
                            strategy = metadata.get('strategy', 'N/A')
                            st.text(f"📋 Strategy: {strategy}")
                        with col3:
                            data_src = metadata.get('data_source', 'N/A')
                            st.text(f"💾 Source: {data_src}")
                        
                        # Row 2: top_k, similarity_threshold, retrieved items
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            top_k = metadata.get('top_k', 'N/A')
                            st.text(f"🔝 top_k: {top_k}")
                        with col2:
                            sim_threshold = metadata.get('similarity_threshold', 'N/A')
                            st.text(f"📊 Threshold: {sim_threshold}")
                        with col3:
                            retrieved = metadata.get('retrieved', metadata.get('total_items', 'N/A'))
                            st.text(f"✅ Retrieved: {retrieved}")
                        
                        # Row 3: Intent, Endpoint, Timestamp
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            intent = metadata.get('intent', 'N/A')
                            st.text(f"🎯 Intent: {intent}")
                        with col2:
                            endpoint = metadata.get('endpoint', 'N/A')
                            st.text(f"🔗 Endpoint: {endpoint}")
                        with col3:
                            timestamp = metadata.get('timestamp', 'N/A')
                            if timestamp != 'N/A' and len(timestamp) > 10:
                                timestamp = timestamp[:19]  # Truncate to datetime
                            st.text(f"🕐 Time: {timestamp}")
                        
                        # Row 4: LLM info if available
                        llm_synthesis = metadata.get('llm_synthesis', 'false')
                        llm_model = metadata.get('llm_model_used', 'none')
                        avg_sim = metadata.get('avg_similarity', 'N/A')
                        
                        if llm_synthesis != 'false' or llm_model != 'none':
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.text(f"🤖 LLM: {llm_model}")
                            with col2:
                                st.text(f"✨ Synthesis: {llm_synthesis}")
                            with col3:
                                st.text(f"📈 Avg Sim: {avg_sim}")
                        
                        # SQL Query if available
                        if metadata.get('sql_query'):
                            st.markdown("**SQL Query:**")
                            st.code(metadata['sql_query'][:200] + "..." if len(metadata['sql_query']) > 200 else metadata['sql_query'])
        else:
            st.info(f"No Q&A pairs found for {data_source} source.")
    
    except Exception as e:
        st.error(f"Error loading Q&A pairs: {str(e)}")
    
    # Close button
    if st.button("Close Explorer", key="close_qa_explorer"):
        st.session_state.show_qa_explorer = False
        st.rerun()

def show_similarity_search():
    """Display similarity search interface"""
    st.markdown("---")
    st.markdown("## 🔍 Similarity Search")
    
    # Search input
    search_query = st.text_input("Enter a question to find similar ones:", key="similarity_search_query")
    
    if search_query:
        # Search options
        col1, col2 = st.columns(2)
        with col1:
            data_source = st.selectbox("Data Source", ["duckdb", "api", "both"], key="similarity_search_source")
        with col2:
            top_k = st.slider("Number of results", 1, 10, 5, key="similarity_search_top_k")
        
        # Intent filter
        intent_filter = st.selectbox("Filter by Intent", ["All", "list_all", "count", "search", "analyze"], key="similarity_search_intent")
        
        if st.button("Search", key="perform_similarity_search"):
            try:
                similar_qa = st.session_state.vector_store.find_similar_qa(
                    question=search_query,
                    data_source=data_source if data_source != "both" else "duckdb",
                    intent=intent_filter if intent_filter != "All" else None,
                    top_k=top_k
                )
                
                if similar_qa:
                    st.markdown(f"**Found {len(similar_qa)} similar questions:**")
                    
                    for i, qa in enumerate(similar_qa):
                        with st.expander(f"Match {i+1}: {qa['similarity']:.1%} similarity", expanded=False):
                            st.markdown(f"**Question:** {qa['question']}")
                            st.markdown(f"**Answer:** {qa['answer'][:300]}...")
                            st.markdown(f"**Similarity:** {qa['similarity']:.1%}")
                            
                            metadata = qa.get('metadata', {})
                            if metadata:
                                st.markdown("**Metadata:**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.text(f"Intent: {metadata.get('intent', 'N/A')}")
                                with col2:
                                    st.text(f"Source: {metadata.get('data_source', 'N/A')}")
                                with col3:
                                    st.text(f"Items: {metadata.get('total_items', 'N/A')}")
                else:
                    st.info("No similar questions found.")
            
            except Exception as e:
                st.error(f"Error searching: {str(e)}")
    
    # Close button
    if st.button("Close Search", key="close_similarity_search"):
        st.session_state.show_similarity_search = False
        st.rerun()

def interfaces_objects_matrix_page():
    """Display Interfaces → Objects Matrix"""
    st.title("🔍 Interfaces → Objects Matrix")
    st.markdown("Analyze which objects (sender, receiver, tags, metadata, properties) are present in each interface.")
    
    # Source selection
    source = st.radio("Data Source", ["Local Engine (DuckDB)", "Local JSON File"], horizontal=True, key="matrix_source")
    
    if source == "Local Engine (DuckDB)":
        duckdb_path = st.text_input("DuckDB database path", value="duckdb_engine/wic.duckdb", key="matrix_duckdb_path")
        
        # Controls
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            detail_limit = st.selectbox("Detail rows limit", [50, 100, 500, 1000, "All"], index=0, key="matrix_detail_limit")
        with col2:
            show_presence = st.checkbox("Show full presence matrix", value=False, key="matrix_show_presence")
        with col3:
            if st.button("Refresh", key="matrix_refresh"):
                st.cache_data.clear()
        
        if st.button("Load Matrix", key="matrix_load"):
            with st.spinner("Loading interfaces-objects matrix..."):
                try:
                    executor = DuckDBExecutor(duckdb_path)
                    limit_val = None if detail_limit == "All" else int(detail_limit)
                    
                    @st.cache_data(ttl=300)
                    def get_cached_matrix(db_path, limit):
                        exec_inst = DuckDBExecutor(db_path)
                        return exec_inst.get_interfaces_objects_matrix(limit=limit)
                    
                    matrix_data = get_cached_matrix(duckdb_path, limit_val)
                    
                    if "error" in matrix_data and matrix_data["error"]:
                        st.error(f"Error: {matrix_data['error']}")
                        return
                    
                    # Summary metrics
                    st.markdown("### 📊 Summary")
                    summary = matrix_data.get("summary", {})
                    
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    with col1:
                        st.metric("Total Interfaces", summary.get("total_interfaces", 0))
                    with col2:
                        st.metric("With Sender", summary.get("interfaces_with_sender", 0))
                    with col3:
                        st.metric("With Receiver", summary.get("interfaces_with_receiver", 0))
                    with col4:
                        st.metric("With Tags", summary.get("interfaces_with_tags", 0))
                    with col5:
                        st.metric("With Metadata", summary.get("interfaces_with_metadata", 0))
                    with col6:
                        st.metric("With Properties", summary.get("interfaces_with_properties", 0))
                    
                    # Coverage percentages
                    total = summary.get("total_interfaces", 1)
                    st.markdown("### 📈 Coverage")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        pct = (summary.get("interfaces_with_sender", 0) / total) * 100
                        st.progress(pct / 100, text=f"Sender: {pct:.1f}%")
                    with col2:
                        pct = (summary.get("interfaces_with_receiver", 0) / total) * 100
                        st.progress(pct / 100, text=f"Receiver: {pct:.1f}%")
                    with col3:
                        pct = (summary.get("interfaces_with_tags", 0) / total) * 100
                        st.progress(pct / 100, text=f"Tags: {pct:.1f}%")
                    with col4:
                        pct = (summary.get("interfaces_with_metadata", 0) / total) * 100
                        st.progress(pct / 100, text=f"Metadata: {pct:.1f}%")
                    with col5:
                        pct = (summary.get("interfaces_with_properties", 0) / total) * 100
                        st.progress(pct / 100, text=f"Properties: {pct:.1f}%")
                    
                    # Detailed view
                    st.markdown("### 📋 Interfaces with Objects Present")
                    detailed = matrix_data.get("detailed", [])
                    
                    if detailed:
                        import pandas as pd
                        df_detailed = pd.DataFrame(detailed)
                        
                        # Add download button
                        csv = df_detailed.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download as CSV",
                            data=csv,
                            file_name="interfaces_objects_detailed.csv",
                            mime="text/csv",
                            key="matrix_download_detailed"
                        )
                        
                        st.dataframe(
                            df_detailed,
                            use_container_width=True,
                            height=400
                        )
                        
                        st.caption(f"Showing {len(detailed)} interfaces with at least one object present")
                    else:
                        st.info("No interfaces with objects found.")
                    
                    # Full presence matrix (optional)
                    if show_presence:
                        st.markdown("### 🔍 Full Presence Matrix")
                        presence = matrix_data.get("presence_matrix", [])
                        
                        if presence:
                            import pandas as pd
                            df_presence = pd.DataFrame(presence)
                            
                            # Add download button
                            csv = df_presence.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Presence Matrix as CSV",
                                data=csv,
                                file_name="interfaces_objects_presence_matrix.csv",
                                mime="text/csv",
                                key="matrix_download_presence"
                            )
                            
                            st.dataframe(
                                df_presence,
                                use_container_width=True,
                                height=600
                            )
                            
                            st.caption(f"Full presence matrix: {len(presence)} interfaces")
                        else:
                            st.info("No presence data available.")
                
                except Exception as e:
                    st.error(f"Error loading matrix: {str(e)}")
                    st.exception(e)
    
    else:  # Local JSON File
        st.info("Matrix analysis for Local JSON File is not yet implemented. Please use DuckDB source.")


def get_local_ollama_models(host: str = "http://localhost:11434") -> list[str]:
    """Get locally available Ollama models with better error handling"""
    import requests
    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [m["name"] for m in data.get("models", []) if "name" in m]
        return models
    except Exception as e:
        print(f"Error fetching Ollama models: {str(e)}")
        return []

def models_page():
    """Display available LLM models and their capabilities"""
    import pandas as pd
    import os
    from src.llm_providers import LLMProviderManager, LLMProvider

    st.title("🤖 LLM Models")
    st.markdown("Browse available language models and their capabilities.")

    # Initialize LLM provider manager
    try:
        llm_manager = LLMProviderManager()
        all_models = llm_manager.get_available_models(show_all=True)
    except Exception as e:
        st.error(f"Error initializing LLM manager: {str(e)}")
        return

    # Get locally available Ollama models
    with st.spinner("Checking for local Ollama models..."):
        local_ollama_models = get_local_ollama_models()
    
    if local_ollama_models:
        st.success(f"Found {len(local_ollama_models)} Ollama models")
        # Show first few models as a preview
        preview_models = local_ollama_models[:5]
        st.info(f"Sample models: {', '.join(preview_models)}{'...' if len(local_ollama_models) > 5 else ''}")
    else:
        st.warning("No Ollama models found. Make sure Ollama is running on localhost:11434")

    # Build model information table
    rows = []
    
    # Add configured models
    for model_name, config in all_models.items():
        # Check if API key is available
        api_key_available = bool(os.getenv(config.api_key_env))
        
        # Check if it's a local Ollama model
        is_local_ollama = config.provider == LLMProvider.OLLAMA
        is_installed = model_name in local_ollama_models if is_local_ollama else True
        
        # Determine availability status
        if is_local_ollama:
            status = "✅ Installed" if is_installed else "❌ Not Installed"
        else:
            status = "✅ Available" if api_key_available else "❌ No API Key"
        
        # Format capabilities
        capabilities = []
        if config.supports_json:
            capabilities.append("JSON")
        if config.supports_images:
            capabilities.append("Images")
        capabilities_str = ", ".join(capabilities) if capabilities else "Text only"
        
        # Format cost
        if config.cost_per_1k_tokens == 0.0:
            cost_str = "Free (Local)"
        else:
            cost_str = f"${config.cost_per_1k_tokens:.4f}/1k tokens"
        
        rows.append({
            "Model": model_name,
            "Provider": config.provider.value.title(),
            "Context": f"{config.context_length:,}",
            "Cost": cost_str,
            "Capabilities": capabilities_str,
            "Status": status,
            "Description": config.description
        })
    
    # Add any additional local Ollama models not in our config
    for model_name in local_ollama_models:
        if not any(row["Model"] == model_name for row in rows):
            rows.append({
                "Model": model_name,
                "Provider": "Ollama",
                "Context": "Unknown",
                "Cost": "Free (Local)",
                "Capabilities": "Text only",
                "Status": "✅ Installed",
                "Description": "Local Ollama model (not in config)"
            })

    if rows:
        df = pd.DataFrame(rows)
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            provider_filter = st.selectbox("Filter by Provider", ["All"] + list(df["Provider"].unique()))
        with col2:
            status_filter = st.selectbox("Filter by Status", ["All"] + list(df["Status"].unique()))
        with col3:
            show_available_only = st.checkbox("Show Available Only", value=True)
        
        # Apply filters
        filtered_df = df.copy()
        if provider_filter != "All":
            filtered_df = filtered_df[filtered_df["Provider"] == provider_filter]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["Status"] == status_filter]
        if show_available_only:
            filtered_df = filtered_df[filtered_df["Status"].str.contains("✅")]
        
        # Display the table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=min(600, 100 + 28 * len(filtered_df)),
            column_config={
                "Model": st.column_config.TextColumn("Model", width="medium"),
                "Provider": st.column_config.TextColumn("Provider", width="small"),
                "Context": st.column_config.TextColumn("Context Length", width="small"),
                "Cost": st.column_config.TextColumn("Cost", width="medium"),
                "Capabilities": st.column_config.TextColumn("Capabilities", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large")
            }
        )
        
        # Summary stats
        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Models", len(df))
        with col2:
            available_count = len(df[df["Status"].str.contains("✅")])
            st.metric("Available", available_count)
        with col3:
            ollama_count = len(df[df["Provider"] == "Ollama"])
            st.metric("Ollama Models", ollama_count)
        with col4:
            free_count = len(df[df["Cost"].str.contains("Free")])
            st.metric("Free Models", free_count)
        
        # Instructions
        st.markdown("### 💡 Usage Tips")
        st.info("""
        - **Green checkmarks (✅)** indicate models ready to use
        - **Red X (❌)** means missing API keys or models not installed
        - **Ollama models** run locally and are free to use
        - **Cloud models** require API keys (set in environment variables)
        - Use the filters above to find models by provider or availability
        """)
        
        # Debug section - show all detected models
        with st.expander("🔍 Debug: All Detected Models", expanded=False):
            st.markdown("**Configured Models:**")
            for model_name, config in all_models.items():
                st.text(f"- {model_name} ({config.provider.value})")
            
            st.markdown("**Local Ollama Models:**")
            for model_name in local_ollama_models:
                st.text(f"- {model_name}")
        
    else:
        st.warning("No models found. Check your configuration.")


def main():
    """Main application"""
    initialize_session_state()
    
    if not st.session_state.authenticated:
        credentials_page()
    else:
        # Sidebar navigation
        with st.sidebar:
            # Vector RAG Configuration
            st.markdown("### ⚙️ Vector RAG Settings")
            
            # Initialize session state for settings if not exists
            if 'vector_rag_top_k' not in st.session_state:
                st.session_state.vector_rag_top_k = 1000
            if 'vector_rag_similarity_threshold' not in st.session_state:
                st.session_state.vector_rag_similarity_threshold = 0.3
            
            # top_k slider
            top_k_value = st.slider(
                "Max Results (top_k)",
                min_value=5,
                max_value=1000,
                value=st.session_state.vector_rag_top_k,
                step=5,
                help="Maximum number of results to return from vector search",
                key="top_k_slider"
            )
            st.session_state.vector_rag_top_k = top_k_value
            
            # similarity_threshold slider
            sim_threshold_value = st.slider(
                "Similarity Threshold",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.vector_rag_similarity_threshold,
                step=0.05,
                help="Minimum similarity score (0-1) for results",
                key="similarity_threshold_slider"
            )
            st.session_state.vector_rag_similarity_threshold = sim_threshold_value
            
            st.markdown("---")
            
            st.markdown("### Navigation")
            page = st.radio(
                "Select Page",
                ["💬 Chat", "🌐 Browser Automation", "🔍 Interfaces → Objects Matrix", "🧩 Models"],
                key="page_navigation"
            )
        
        if page == "💬 Chat":
            chat_page()
        elif page == "🌐 Browser Automation":
            from src.browser_automation_page import browser_automation_page
            browser_automation_page()
        elif page == "🔍 Interfaces → Objects Matrix":
            interfaces_objects_matrix_page()
        elif page == "🧩 Models":
            models_page()

if __name__ == "__main__":
    main()