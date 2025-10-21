"""
Module: llm_providers

Purpose:
    Centralize multi-provider LLM management including model catalogs, client
    initialization, request routing, failover, chunking strategies, and cost/
    speed trade-offs.

Key Concepts:
    - Provider-agnostic `LLMProviderManager` with a catalog of `ModelConfig`
    - Dynamic client initialization based on environment configuration
    - Fallback strategies and cycling across models to mitigate rate limits
    - Chunking utilities aligned with model context sizes

Public API:
    - `LLMProvider`, `ModelConfig`, `ChunkingConfig`
    - `LLMProviderManager`: core class for selection and generation

Inputs/Outputs:
    - Inputs: Provider API keys via environment; user/system prompts and options
    - Outputs: Generated text; metadata about models, providers, and processing

Dependencies:
    - External: OpenAI, Google Gemini, Anthropic, Groq, OpenRouter, optional Ollama

Usage:
    >>> mgr = LLMProviderManager()
    >>> model = mgr.get_best_model_for_task(estimated_tokens=5000)
    >>> text = mgr.generate_response(model, "You are helpful.", "Hello!")
"""

import json
import os
import requests
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
load_dotenv()
# Import all provider libraries
from openai import OpenAI

# Google imports
GOOGLE_AVAILABLE = False
genai = None
types = None
try:
    from google import genai
    from google.genai import types
    GOOGLE_AVAILABLE = True
except ImportError:
    pass

# Anthropic imports
ANTHROPIC_AVAILABLE = False
Anthropic = None
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

# Groq imports
GROQ_AVAILABLE = False
Groq = None
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    pass

# Ollama imports
OLLAMA_AVAILABLE = False
try:
    # Test if Ollama is running
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    OLLAMA_AVAILABLE = response.status_code == 200
except:
    OLLAMA_AVAILABLE = False


class LLMProvider(Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: LLMProvider
    context_length: int
    cost_per_1k_tokens: float
    supports_json: bool
    supports_images: bool
    api_key_env: str
    description: str

@dataclass
class ChunkingConfig:
    """Configuration for text chunking and processing"""
    overlap_ratio: float = 0.15          # 15% overlap between chunks
    max_depth: int = 3                   # Maximum recursive depth
    context_usage_ratio: float = 0.7     # Use 70% of context for chunk content
    prefer_sentence_breaks: bool = True   # Try to break at sentence boundaries
    min_chunk_size: int = 100            # Minimum chunk size in tokens
    max_chunk_size: Optional[int] = None # Maximum chunk size (None = use model limit)
    temperature: float = 0.1             # Default temperature for processing
    include_free_models: bool = False    # Include free models in cycling
    prefer_fast_models: bool = True      # Prioritize fast models
    parallel_processing: bool = False    # Enable parallel chunk processing (future feature)


class LLMProviderManager:
    """Manages multiple LLM providers and model selection"""
    
    def __init__(self):
        self.models = {
            # OpenAI Models
            "gpt-4o": ModelConfig(
                name="gpt-4o",
                provider=LLMProvider.OPENAI,
                context_length=128000,
                cost_per_1k_tokens=0.015,
                supports_json=True,
                supports_images=True,
                api_key_env="OPENAI_API_KEY",
                description="GPT-4O - Latest OpenAI model with vision"
            ),
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                provider=LLMProvider.OPENAI,
                context_length=128000,
                cost_per_1k_tokens=0.0015,
                supports_json=True,
                supports_images=True,
                api_key_env="OPENAI_API_KEY",
                description="GPT-4O Mini - Cost-effective OpenAI model"
            ),
            
            # Google Models
            "gemini-2.0-flash": ModelConfig(
                name="gemini-2.0-flash",
                provider=LLMProvider.GOOGLE,
                context_length=2000000,  # 2M context
                cost_per_1k_tokens=0.00025,
                supports_json=True,
                supports_images=True,
                api_key_env="GEMINI_API_KEY",
                description="Gemini 2.0 Flash - Ultra-high context, fast inference"
            ),
            "gemini-2.5-pro": ModelConfig(
                name="gemini-2.5-pro",
                provider=LLMProvider.GOOGLE,
                context_length=2000000,  # 2M context
                cost_per_1k_tokens=0.00125,
                supports_json=True,
                supports_images=True,
                api_key_env="GEMINI_API_KEY",
                description="Gemini 2.5 Pro - Ultra-high context, advanced reasoning"
            ),
            
            # Anthropic Models
            "claude-3-5-sonnet-20241022": ModelConfig(
                name="claude-3-5-sonnet-20241022",
                provider=LLMProvider.ANTHROPIC,
                context_length=200000,
                cost_per_1k_tokens=0.015,
                supports_json=True,
                supports_images=True,
                api_key_env="ANTHROPIC_API_KEY",
                description="Claude 3.5 Sonnet - High context, excellent reasoning"
            ),
            
            # Groq Models (fast inference)
            "llama-3.3-70b-versatile": ModelConfig(
                name="llama-3.3-70b-versatile",
                provider=LLMProvider.GROQ,
                context_length=131072,
                cost_per_1k_tokens=0.0008,
                supports_json=True,
                supports_images=False,
                api_key_env="GROQ_API_KEY",
                description="Llama 3.3 70B - Fast inference, high context"
            ),
            "llama-3.1-8b-instant": ModelConfig(
                name="llama-3.1-8b-instant",
                provider=LLMProvider.GROQ,
                context_length=131072,
                cost_per_1k_tokens=0.0001,
                supports_json=True,
                supports_images=False,
                api_key_env="GROQ_API_KEY",
                description="Llama 3.1 8B - Ultra-fast inference, cost-effective"
            ),
            
            # OpenRouter Models (OpenAI-compatible)
            "openai/gpt-4o-mini": ModelConfig(
                name="openai/gpt-4o-mini",
                provider=LLMProvider.OPENROUTER,
                context_length=128000,
                cost_per_1k_tokens=0.00015,
                supports_json=True,
                supports_images=True,
                api_key_env="OPENROUTER_API_KEY",
                description="GPT-4o Mini via OpenRouter - Reliable and fast"
            ),
            "google/gemini-2.0-flash-exp:free": ModelConfig(
                name="google/gemini-2.0-flash-exp:free",
                provider=LLMProvider.OPENROUTER,
                context_length=1048576,
                cost_per_1k_tokens=0.0,
                supports_json=True,
                supports_images=True,
                api_key_env="OPENROUTER_API_KEY",
                description="⚠️ Gemini 2.0 Flash Experimental - Free tier (often rate-limited)"
            ),
            "meta-llama/llama-3.1-405b-instruct": ModelConfig(
                name="meta-llama/llama-3.1-405b-instruct",
                provider=LLMProvider.OPENROUTER,
                context_length=131072,
                cost_per_1k_tokens=0.0054,
                supports_json=True,
                supports_images=False,
                api_key_env="OPENROUTER_API_KEY",
                description="Llama 3.1 405B - Largest open model, excellent performance"
            ),
            "mistralai/mistral-nemo:free": ModelConfig(
                name="mistralai/mistral-nemo:free",
                provider=LLMProvider.OPENROUTER,
                context_length=1048576,
                cost_per_1k_tokens=0.0054,
                supports_json=True,
                supports_images=False,
                api_key_env="OPENROUTER_API_KEY",
                description="mistralai/mistral-nemo:free"
            ),
            
            # Ollama Models (Local) - GPT-4o Equivalent Performance
            "llama3.2:latest": ModelConfig(
                name="llama3.2:latest",
                provider=LLMProvider.OLLAMA,
                context_length=128000,
                cost_per_1k_tokens=0.0,  # Free - local model
                supports_json=True,
                supports_images=False,
                api_key_env="OLLAMA_BASE_URL",  # Optional, defaults to localhost:11434
                description="🏆 Llama 3.2 - Excellent for analysis tasks, GPT-4o equivalent"
            ),
            "deepseek-r1:14b": ModelConfig(
                name="deepseek-r1:14b",
                provider=LLMProvider.OLLAMA,
                context_length=128000,
                cost_per_1k_tokens=0.0,
                supports_json=True,
                supports_images=False,
                api_key_env="OLLAMA_BASE_URL",
                description="🧠 DeepSeek R1 14B - Excellent reasoning, matches GPT-4o performance"
            ),
            "qwen2.5:14b": ModelConfig(
                name="qwen2.5:14b",
                provider=LLMProvider.OLLAMA,
                context_length=32768,
                cost_per_1k_tokens=0.0,
                supports_json=True,
                supports_images=False,
                api_key_env="OLLAMA_BASE_URL",
                description="📊 Qwen 2.5 14B - Great for data analysis and reasoning"
            ),
            "llama3.1:8b": ModelConfig(
                name="llama3.1:8b",
                provider=LLMProvider.OLLAMA,
                context_length=128000,
                cost_per_1k_tokens=0.0,
                supports_json=True,
                supports_images=False,
                api_key_env="OLLAMA_BASE_URL",
                description="⚡ Llama 3.1 8B - Fast and efficient for most tasks"
            ),
            "mistral:7b": ModelConfig(
                name="mistral:7b",
                provider=LLMProvider.OLLAMA,
                context_length=32768,
                cost_per_1k_tokens=0.0,
                supports_json=True,
                supports_images=False,
                api_key_env="OLLAMA_BASE_URL",
                description="🚀 Mistral 7B - Lightweight but capable model"
            ),
        }
        
        self.clients = {}
        self.initialize_clients()
    
    def initialize_clients(self):
        """Initialize all available clients"""
        print(f"[DEBUG] Initializing clients...")
        print(f"[DEBUG] GROQ_AVAILABLE: {GROQ_AVAILABLE}")
        print(f"[DEBUG] GROQ_API_KEY present: {bool(os.getenv('GROQ_API_KEY'))}")
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self.clients[LLMProvider.OPENAI] = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print(f"[DEBUG] OpenAI client initialized")
        
        # Google Gemini
        if GOOGLE_AVAILABLE and os.getenv("GEMINI_API_KEY"):
            self.clients[LLMProvider.GOOGLE] = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            print(f"[DEBUG] Google client initialized")
        
        # Anthropic
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            self.clients[LLMProvider.ANTHROPIC] = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            print(f"[DEBUG] Anthropic client initialized")
        
        # Groq
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            if GROQ_AVAILABLE:
                try:
                    self.clients[LLMProvider.GROQ] = Groq(api_key=groq_api_key)
                    print(f"[DEBUG] Groq client initialized successfully")
                except Exception as e:
                    print(f"[ERROR] Failed to initialize Groq client: {str(e)}")
            else:
                print(f"[ERROR] Groq package not available. Install with: pip install groq")
        else:
            print(f"[ERROR] GROQ_API_KEY not found in environment")
        
        # OpenRouter (OpenAI-compatible)
        if os.getenv("OPENROUTER_API_KEY"):
            self.clients[LLMProvider.OPENROUTER] = OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
            print(f"[DEBUG] OpenRouter client initialized")
        
        # Ollama (Local)
        if OLLAMA_AVAILABLE:
            self.clients[LLMProvider.OLLAMA] = {
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            }
            print(f"[DEBUG] Ollama client initialized")
    
    def get_available_models(self, show_all: bool = True) -> Dict[str, ModelConfig]:
        """
        Return all models if show_all is True, otherwise only those with available API keys.
        """
        if show_all:
            return self.models
        else:
            available = {}
            for name, config in self.models.items():
                if os.getenv(config.api_key_env):
                    available[name] = config
            return available

    def check_api_key_for_model(self, model_name: str) -> bool:
        """
        Check if the required API key for the given model is set.
        For Ollama models, check if the Ollama service is accessible instead.
        """
        config = self.models.get(model_name)
        
        # If model not in config, check if it's a dynamic Ollama model
        if not config:
            # Check if it's a dynamic Ollama model by testing if Ollama service is accessible
            try:
                import requests
                ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                response = requests.get(f"{ollama_url}/api/tags", timeout=3)
                if response.status_code == 200:
                    # Check if this model exists in Ollama
                    models = [m["name"] for m in response.json().get("models", [])]
                    if model_name in models:
                        return True  # It's a valid Ollama model
                return False
            except:
                return False
        
        # Special handling for Ollama models
        if config.provider == LLMProvider.OLLAMA:
            # For Ollama, check if the service is accessible rather than requiring an API key
            try:
                import requests
                ollama_url = os.getenv(config.api_key_env, "http://localhost:11434")
                response = requests.get(f"{ollama_url}/api/tags", timeout=3)
                return response.status_code == 200
            except:
                return False
        
        # For all other providers, check if API key is set
        return bool(os.getenv(config.api_key_env))
    
    def get_high_context_models(self, min_context: int = 200000) -> Dict[str, ModelConfig]:
        """Get models with high context length"""
        available = self.get_available_models()
        return {name: config for name, config in available.items() 
                if config.context_length >= min_context}
    
    def get_best_model_for_task(self, estimated_tokens: int, prefer_cost: bool = False) -> Optional[str]:
        """Select the best model for a given task"""
        available = self.get_available_models()
        
        if not available:
            return None
        
        # Filter models that can handle the token count
        suitable = {name: config for name, config in available.items() 
                   if config.context_length >= estimated_tokens}
        
        if not suitable:
            return None
        
        if prefer_cost:
            # Sort by cost (lowest first)
            return min(suitable.keys(), key=lambda x: suitable[x].cost_per_1k_tokens)
        else:
            # Sort by context length (highest first) for complex tasks
            return max(suitable.keys(), key=lambda x: suitable[x].context_length)
    
    def generate_response_with_fallback(self, model_name: str, system_prompt: str, user_prompt: str, 
                                       temperature: float = 0.1, max_tokens: Optional[int] = None) -> Tuple[str, str]:
        """Generate response with automatic fallback to alternative models"""
        models_to_try = [model_name] + self.get_alternative_models(model_name)
        
        for i, current_model in enumerate(models_to_try[:3]):  # Try up to 3 models
            try:
                response = self.generate_response(current_model, system_prompt, user_prompt, temperature, max_tokens)
                return response, current_model
            except Exception as e:
                print(f"[DEBUG] ❌ Exception with {current_model}: {str(e)}")
                if i == len(models_to_try) - 1:  # Last model
                    raise e
                else:
                    print(f"[DEBUG] 🔄 Trying fallback model: {models_to_try[i+1]}")
                    continue
        
        raise Exception("All models failed")
    
    def generate_response(self, model_name: str, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.1, max_tokens: Optional[int] = None) -> str:
        """Generate response using specified model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        config = self.models[model_name]
        
        if config.provider not in self.clients:
            raise ValueError(f"Provider {config.provider.value} not available (missing API key)")
        
        client = self.clients[config.provider]
        
        try:
            if config.provider == LLMProvider.OPENAI or config.provider == LLMProvider.OPENROUTER or config.provider == LLMProvider.GROQ:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                # Better error handling for malformed responses
                if response and response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content and isinstance(content, str) and len(content.strip()) > 0:
                        return content
                    else:
                        raise Exception("Empty or invalid response content")
                else:
                    raise Exception("Malformed API response structure")
            
            elif config.provider == LLMProvider.GOOGLE:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=f"{system_prompt}\n\n{user_prompt}")])
                    ],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                )
                return response.text or ""
            
            elif config.provider == LLMProvider.ANTHROPIC:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens or 4096,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.content[0].text or ""
            
            elif config.provider == LLMProvider.OLLAMA:
                base_url = client["base_url"]
                payload = {
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant:",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens or 4096
                    }
                }
                
                response = requests.post(
                    f"{base_url}/api/generate",
                    json=payload,
                    timeout=300  # 5 minute timeout for local models
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            
            else:
                raise ValueError(f"Provider {config.provider.value} not implemented")
                
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific error types
            if "429" in error_msg or "rate" in error_msg.lower():
                # Rate limit error - suggest alternatives
                alternatives = self.get_alternative_models(model_name)
                alt_text = f"\n\nSuggested alternatives: {', '.join(alternatives[:3])}" if alternatives else ""
                raise Exception(f"Rate limit exceeded for {model_name}. This model is temporarily unavailable.{alt_text}")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise Exception(f"Authentication failed for {model_name}. Please check your API key.")
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(f"Model {model_name} not found or unavailable.")
            else:
                raise Exception(f"Error generating response with {model_name}: {error_msg}")
    
    def get_alternative_models(self, failed_model: str) -> List[str]:
        """Get alternative models when one fails"""
        available_models = []
        
        for model_name, config in self.models.items():
            if (model_name != failed_model and 
                config.provider in self.clients and
                not ("free" in model_name.lower() and "rate" in model_name.lower())):
                available_models.append(model_name)
        
        # Sort by preference: OpenAI, then others, then free models last
        def sort_key(model):
            if "gpt-4o-mini" in model:
                return 0  # Highest priority
            elif "openai" in model:
                return 1
            elif "groq" in model or "llama" in model:
                return 2
            elif "free" in model:
                return 9  # Lowest priority
            else:
                return 5
        
        return sorted(available_models, key=sort_key)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def should_use_chunking(self, model_name: str, estimated_tokens: int) -> bool:
        """Determine if chunking is needed for a model"""
        if model_name not in self.models:
            return True
        
        config = self.models[model_name]
        # Use 80% of context length as safety margin
        return estimated_tokens > (config.context_length * 0.8)
    
    def get_optimal_chunk_size(self, model_name: str, overlap_ratio: float = 0.1) -> Tuple[int, int]:
        """Get optimal chunk size and overlap for a model"""
        if model_name not in self.models:
            # Default for unknown models
            return 4000, 400
        
        config = self.models[model_name]
        # Use 70% of context length for chunk, leaving room for system prompt and response
        base_chunk_size = int(config.context_length * 0.7)
        overlap_size = int(base_chunk_size * overlap_ratio)
        
        return base_chunk_size, overlap_size
    
    def create_overlapping_chunks(self, text: str, model_name: str, overlap_ratio: float = 0.15) -> List[Dict[str, Any]]:
        """Create overlapping text chunks optimized for the model's context length"""
        chunk_size, overlap_size = self.get_optimal_chunk_size(model_name, overlap_ratio)
        
        # Convert to character-based chunking (rough token estimation)
        char_chunk_size = chunk_size * 4  # ~4 chars per token
        char_overlap_size = overlap_size * 4
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + char_chunk_size, len(text))
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within the last 20% of the chunk
                search_start = max(start, end - int(char_chunk_size * 0.2))
                sentence_end = max(
                    text.rfind('.', search_start, end),
                    text.rfind('!', search_start, end),
                    text.rfind('?', search_start, end)
                )
                if sentence_end > search_start:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    'index': chunk_index,
                    'text': chunk_text,
                    'start_pos': start,
                    'end_pos': end,
                    'estimated_tokens': self.estimate_tokens(chunk_text),
                    'overlap_with_previous': start > 0,
                    'overlap_with_next': end < len(text)
                })
                chunk_index += 1
            
            # Move start position with overlap
            if end >= len(text):
                break
            start = max(start + 1, end - char_overlap_size)
        
        return chunks
    
    def create_recursive_chunks(self, text: str, model_name: str, max_depth: int = 3, 
                              overlap_ratio: float = 0.15) -> Dict[str, List[Dict[str, Any]]]:
        """Create recursive chunks at multiple levels for hierarchical processing"""
        all_chunks = {}
        
        # Level 0: Original text
        all_chunks['level_0'] = [{'index': 0, 'text': text, 'estimated_tokens': self.estimate_tokens(text)}]
        
        current_texts = [text]
        
        for level in range(1, max_depth + 1):
            level_chunks = []
            
            for parent_index, parent_text in enumerate(current_texts):
                if self.should_use_chunking(model_name, self.estimate_tokens(parent_text)):
                    # Create chunks for this text
                    chunks = self.create_overlapping_chunks(parent_text, model_name, overlap_ratio)
                    
                    for chunk in chunks:
                        chunk['parent_index'] = parent_index
                        chunk['level'] = level
                        level_chunks.append(chunk)
                else:
                    # Text is small enough, keep as is
                    level_chunks.append({
                        'index': len(level_chunks),
                        'text': parent_text,
                        'parent_index': parent_index,
                        'level': level,
                        'estimated_tokens': self.estimate_tokens(parent_text),
                        'no_chunking_needed': True
                    })
            
            all_chunks[f'level_{level}'] = level_chunks
            
            # Prepare for next level
            current_texts = [chunk['text'] for chunk in level_chunks]
            
            # Stop if no chunking was needed at this level
            if all(chunk.get('no_chunking_needed', False) for chunk in level_chunks):
                break
        
        return all_chunks
    
    def process_chunks_with_cycling(self, chunks: List[Dict[str, Any]], system_prompt: str, 
                                   available_models: List[str], temperature: float = 0.1, 
                                   max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process chunks using model cycling to avoid rate limits"""
        results = []
        current_model_index = 0
        
        for i, chunk in enumerate(chunks):
            # Cycle through available models
            model_name = available_models[current_model_index % len(available_models)]
            
            try:
                print(f"[DEBUG] Processing chunk {i+1}/{len(chunks)} with {model_name}")
                
                # Create user prompt with chunk context
                user_prompt = f"""
Chunk {chunk['index'] + 1} of {len(chunks)}:
Estimated tokens: {chunk['estimated_tokens']}
{'(Overlaps with previous)' if chunk.get('overlap_with_previous') else ''}
{'(Overlaps with next)' if chunk.get('overlap_with_next') else ''}

Content:
{chunk['text']}
"""
                
                response = self.generate_response(
                    model_name, system_prompt, user_prompt, temperature, max_tokens
                )
                
                results.append({
                    'chunk_index': chunk['index'],
                    'model_used': model_name,
                    'input_tokens': chunk['estimated_tokens'],
                    'response': response,
                    'success': True,
                    'chunk_metadata': chunk
                })
                
                # Move to next model for next chunk
                current_model_index += 1
                
            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i+1} with {model_name}: {str(e)}")
                
                # Try with fallback
                try:
                    response, used_model = self.generate_response_with_fallback(
                        model_name, system_prompt, user_prompt, temperature, max_tokens
                    )
                    
                    results.append({
                        'chunk_index': chunk['index'],
                        'model_used': used_model,
                        'input_tokens': chunk['estimated_tokens'],
                        'response': response,
                        'success': True,
                        'fallback_used': True,
                        'chunk_metadata': chunk
                    })
                    
                except Exception as fallback_error:
                    results.append({
                        'chunk_index': chunk['index'],
                        'model_used': model_name,
                        'input_tokens': chunk['estimated_tokens'],
                        'response': '',
                        'success': False,
                        'error': str(fallback_error),
                        'chunk_metadata': chunk
                    })
                
                # Still move to next model
                current_model_index += 1
        
        return results
    
    def recursive_summarization(self, text: str, system_prompt: str, available_models: List[str],
                               max_depth: int = 3, overlap_ratio: float = 0.15, 
                               temperature: float = 0.1) -> Dict[str, Any]:
        """Perform recursive summarization with overlapping chunks"""
        
        # Create recursive chunks
        all_chunks = self.create_recursive_chunks(text, available_models[0], max_depth, overlap_ratio)
        
        results = {
            'original_text_tokens': self.estimate_tokens(text),
            'levels_processed': len(all_chunks),
            'chunk_structure': {},
            'level_results': {},
            'final_summary': ''
        }
        
        # Process each level
        for level_key in sorted(all_chunks.keys()):
            level_num = int(level_key.split('_')[1])
            chunks = all_chunks[level_key]
            
            print(f"[DEBUG] Processing {level_key} with {len(chunks)} chunks")
            
            results['chunk_structure'][level_key] = {
                'chunk_count': len(chunks),
                'total_tokens': sum(chunk['estimated_tokens'] for chunk in chunks),
                'avg_tokens_per_chunk': sum(chunk['estimated_tokens'] for chunk in chunks) / len(chunks) if chunks else 0
            }
            
            if level_num == 0:
                # Level 0 is just the original text
                results['level_results'][level_key] = [{
                    'chunk_index': 0,
                    'response': 'Original text (not processed)',
                    'success': True,
                    'chunk_metadata': chunks[0]
                }]
            else:
                # Process chunks with model cycling
                level_results = self.process_chunks_with_cycling(
                    chunks, system_prompt, available_models, temperature
                )
                results['level_results'][level_key] = level_results
                
                # If this is the final level, combine results for final summary
                if level_num == len(all_chunks) - 1:
                    successful_responses = [r['response'] for r in level_results if r['success']]
                    if successful_responses:
                        # Create final summary by combining all successful chunk summaries
                        combined_text = '\n\n'.join(successful_responses)
                        
                        # Use the first available model for final synthesis
                        try:
                            final_summary_prompt = """
Combine and synthesize the following chunk summaries into a comprehensive final summary.
Ensure coherence and remove any redundancy from overlapping chunks:

"""
                            final_summary = self.generate_response(
                                available_models[0], system_prompt, 
                                final_summary_prompt + combined_text, temperature
                            )
                            results['final_summary'] = final_summary
                        except Exception as e:
                            results['final_summary'] = f"Error creating final summary: {str(e)}"
                            results['fallback_summary'] = combined_text
        
        return results
    
    def get_available_models_for_cycling(self, prefer_fast: bool = True, include_free: bool = False) -> List[str]:
        """Get list of available models optimized for cycling"""
        available = []
        
        for model_name, config in self.models.items():
            if config.provider in self.clients:
                # Skip free models unless explicitly requested (they're often rate-limited)
                if not include_free and "free" in model_name.lower():
                    continue
                available.append(model_name)
        
        if prefer_fast:
            # Sort by speed/cost preference for cycling
            def speed_priority(model):
                if "gpt-4o-mini" in model or "llama-3.1-8b" in model:
                    return 0  # Fastest
                elif "groq" in model or "instant" in model:
                    return 1  # Very fast
                elif "mini" in model or "8b" in model:
                    return 2  # Fast
                elif "flash" in model:
                    return 3  # Medium
                else:
                    return 4  # Slower but capable
            
            available.sort(key=speed_priority)
        
        return available
    
    def estimate_processing_time(self, text: str, models: List[str]) -> Dict[str, Any]:
        """Estimate processing time and costs for chunked processing"""
        total_tokens = self.estimate_tokens(text)
        
        # Get chunk info for the first model (representative)
        if models:
            chunks = self.create_overlapping_chunks(text, models[0])
            chunk_count = len(chunks)
        else:
            chunk_count = 1
            chunks = []
        
        # Rough time estimates (seconds per 1k tokens)
        time_estimates = {
            'groq': 0.5,      # Very fast
            'gpt-4o-mini': 2,  # Fast
            'gemini': 3,       # Medium
            'claude': 4,       # Slower
            'ollama': 10,      # Local, varies
            'default': 5
        }
        
        total_cost = 0
        total_time = 0
        
        for i, model in enumerate(models):
            # Estimate which chunks this model will process
            chunks_for_model = [c for j, c in enumerate(chunks) if j % len(models) == i]
            model_tokens = sum(c['estimated_tokens'] for c in chunks_for_model)
            
            # Get time estimate
            time_key = next((k for k in time_estimates.keys() if k in model.lower()), 'default')
            model_time = (model_tokens / 1000) * time_estimates[time_key]
            total_time = max(total_time, model_time)  # Parallel processing
            
            # Get cost estimate
            if model in self.models:
                model_cost = (model_tokens / 1000) * self.models[model].cost_per_1k_tokens
                total_cost += model_cost
        
        return {
            'total_tokens': total_tokens,
            'chunk_count': chunk_count,
            'estimated_time_seconds': total_time,
            'estimated_cost_usd': total_cost,
            'models_used': models,
            'chunks_per_model': chunk_count // len(models) if models else 0
        }
    
    def smart_summarization(self, text: str, system_prompt: str, config: ChunkingConfig = None) -> Dict[str, Any]:
        """Smart summarization using optimal chunking and model cycling"""
        if config is None:
            config = ChunkingConfig()
        
        # Get available models based on config
        available_models = self.get_available_models_for_cycling(
            prefer_fast=config.prefer_fast_models,
            include_free=config.include_free_models
        )
        
        if not available_models:
            raise ValueError("No models available for processing")
        
        # Estimate processing requirements
        estimates = self.estimate_processing_time(text, available_models[:3])
        
        # Perform recursive summarization
        result = self.recursive_summarization(
            text=text,
            system_prompt=system_prompt,
            available_models=available_models,
            max_depth=config.max_depth,
            overlap_ratio=config.overlap_ratio,
            temperature=config.temperature
        )
        
        # Add processing estimates to result
        result['processing_estimates'] = estimates
        result['config_used'] = config
        
        return result
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        if model_name not in self.models:
            return {}
        
        config = self.models[model_name]
        return {
            "name": config.name,
            "provider": config.provider.value,
            "context_length": config.context_length,
            "cost_per_1k_tokens": config.cost_per_1k_tokens,
            "supports_json": config.supports_json,
            "supports_images": config.supports_images,
            "description": config.description,
            "available": config.provider in self.clients
        }
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        for provider in LLMProvider:
            env_key = None
            for config in self.models.values():
                if config.provider == provider:
                    env_key = config.api_key_env
                    break
            
            status[provider.value] = {
                "available": provider in self.clients,
                "api_key_env": env_key,
                "api_key_set": bool(os.getenv(env_key)) if env_key else False,
                "models": [name for name, config in self.models.items() if config.provider == provider]
            }
        
        return status

    def get_llm_client(self, model_name: str):
        """
        Return the client for the provider associated with the given model name.
        """
        config = self.models.get(model_name)
        if not config:
            raise ValueError(f"Model {model_name} not found")
        client = self.clients.get(config.provider)
        if not client:
            raise ValueError(f"Provider {config.provider.value} not available (missing API key)")
        return client