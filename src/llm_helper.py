"""
Module: llm_helper

Purpose:
    Provide a lightweight abstraction over multiple LLM providers with a
    consistent API for capability discovery and text generation. Chooses the
    best available model by context length or preference and exposes helpers
    for token estimation and chunking decisions.

Key Concepts:
    - Provider availability discovery via environment variables/import checks
    - Model selection by context length or first-available heuristic
    - Unified chat-completions interface across providers

Public API:
    - `get_available_providers`, `get_best_available_model`
    - `generate_llm_response` (one-shot chat completion)
    - `estimate_tokens`, `should_use_chunking`

Inputs/Outputs:
    - Inputs: Env vars like `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`,
      `GROQ_API_KEY`, `OPENROUTER_API_KEY`.
    - Outputs: Text responses from provider chat APIs.

Dependencies:
    - External: OpenAI, Google Gemini, Anthropic, Groq (optional), OpenRouter.

Usage:
    >>> model = get_best_available_model()
    >>> text = generate_llm_response("Hello", system_prompt="You are helpful.", model=model)
"""

import os
import json
from typing import Optional, Dict, Any
from openai import OpenAI

# Try to import optional providers
try:
    from google import genai
    from google.genai import types
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """Get information about available LLM providers"""
    providers = {
        "openai": {
            "available": bool(os.getenv("OPENAI_API_KEY")),
            "models": ["gpt-4o", "gpt-4o-mini"],
            "context_lengths": {"gpt-4o": 128000, "gpt-4o-mini": 128000},
            "description": "OpenAI GPT-4O models (128k context)"
        },
        "google": {
            "available": GOOGLE_AVAILABLE and bool(os.getenv("GEMINI_API_KEY")),
            "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
            "context_lengths": {"gemini-2.5-flash": 2000000, "gemini-2.5-pro": 2000000},
            "description": "Google Gemini 2.0 models (2M context)"
        },
        "anthropic": {
            "available": ANTHROPIC_AVAILABLE and bool(os.getenv("ANTHROPIC_API_KEY")),
            "models": ["claude-3-5-sonnet-20241022"],
            "context_lengths": {"claude-3-5-sonnet-20241022": 200000},
            "description": "Anthropic Claude 3.5 Sonnet (200k context)"
        },
        "groq": {
            "available": GROQ_AVAILABLE and bool(os.getenv("GROQ_API_KEY")),
            "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
            "context_lengths": {"llama-3.1-70b-versatile": 131072, "llama-3.1-8b-instant": 131072},
            "description": "Groq Llama 3.1 models (fast inference, 131k context)"
        },
        "openrouter": {
            "available": bool(os.getenv("OPENROUTER_API_KEY")),
            "models": ["deepseek/deepseek-chat", "meta-llama/llama-3.1-405b-instruct"],
            "context_lengths": {"deepseek/deepseek-chat": 128000, "meta-llama/llama-3.1-405b-instruct": 131072},
            "description": "OpenRouter models (DeepSeek, Llama 405B)"
        }
    }
    return providers


def get_best_available_model(prefer_context: bool = True) -> Optional[str]:
    """Get the best available model based on preferences"""
    providers = get_available_providers()
    
    available_models = []
    for provider, info in providers.items():
        if info["available"]:
            for model in info["models"]:
                context_length = info["context_lengths"].get(model, 0)
                available_models.append({
                    "provider": provider,
                    "model": model,
                    "context_length": context_length
                })
    
    if not available_models:
        return None
    
    if prefer_context:
        # Sort by context length (highest first)
        best = max(available_models, key=lambda x: x["context_length"])
    else:
        # Just return first available
        best = available_models[0]
    
    return f"{best['provider']}:{best['model']}"


def generate_llm_response(prompt: str, system_prompt: str = "", model: Optional[str] = None) -> str:
    """Generate response using specified or best available model"""
    
    if not model:
        model = get_best_available_model()
        if not model:
            raise Exception("No LLM providers available. Please add API keys.")
    
    provider, model_name = model.split(":", 1)
    
    try:
        if provider == "openai":
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content or ""
        
        elif provider == "google" and GOOGLE_AVAILABLE:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            return response.text or ""
        
        elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model_name,
                max_tokens=4096,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text if response.content else ""
        
        elif provider == "groq" and GROQ_AVAILABLE:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content or ""
        
        elif provider == "openrouter":
            client = OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content or ""
        
        else:
            raise Exception(f"Provider {provider} not available or not supported")
            
    except Exception as e:
        raise Exception(f"Error with {provider}:{model_name}: {str(e)}")


def estimate_tokens(text: str) -> int:
    """Rough token estimation"""
    return len(text) // 4


def should_use_chunking(text: str, model: Optional[str] = None) -> bool:
    """Determine if text needs chunking for the model"""
    if not model:
        model = get_best_available_model()
        if not model:
            return True
    
    provider, model_name = model.split(":", 1)
    providers = get_available_providers()
    
    if provider in providers and model_name in providers[provider]["context_lengths"]:
        max_context = providers[provider]["context_lengths"][model_name]
        estimated_tokens = estimate_tokens(text)
        # Use 80% of context as safety margin
        return estimated_tokens > (max_context * 0.8)
    
    return True  # Default to chunking if unsure