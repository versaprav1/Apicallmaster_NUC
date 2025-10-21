#!/usr/bin/env python3
"""
Quick test to check which models are available
"""

import sys
import os
sys.path.append('src')

from llm_providers import LLMProviderManager

def test_available_models():
    """Test which models are currently available"""
    print("Testing available models...")
    
    try:
        manager = LLMProviderManager()
        
        print("\n=== Provider Status ===")
        status = manager.get_provider_status()
        for provider, info in status.items():
            print(f"{provider}: {'✅' if info['available'] else '❌'} (API Key: {'✅' if info['api_key_set'] else '❌'})")
        
        print("\n=== Available Models ===")
        available_models = []
        for model_name in manager.models.keys():
            model_info = manager.get_model_info(model_name)
            if model_info['available']:
                available_models.append(model_name)
                print(f"✅ {model_name} - {model_info['description']}")
            else:
                print(f"❌ {model_name} - {model_info['description']}")
        
        print(f"\n=== Summary ===")
        print(f"Total models: {len(manager.models)}")
        print(f"Available models: {len(available_models)}")
        
        if available_models:
            print(f"\nRecommended models to try:")
            for model in available_models[:5]:  # Top 5
                print(f"  - {model}")
        
        return available_models
        
    except Exception as e:
        print(f"Error testing models: {str(e)}")
        return []

if __name__ == "__main__":
    test_available_models()