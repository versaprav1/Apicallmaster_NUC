#!/usr/bin/env python3
"""
Example usage of the enhanced LLM provider with chunking and cycling
"""

import sys
import os
sys.path.append('src')

from llm_providers import LLMProviderManager, ChunkingConfig

def example_basic_usage():
    """Basic example of using the enhanced features"""
    
    # Sample text (you can replace this with your actual content)
    long_text = """
    Your long document content goes here. This could be:
    - Research papers
    - Meeting transcripts
    - Large datasets
    - Documentation
    - Books or articles
    - Any text that exceeds model context limits
    
    The system will automatically chunk this content based on the model's
    context length and process it using multiple models to avoid rate limits.
    """ * 20  # Make it longer for demonstration
    
    print("=== Basic Smart Summarization Example ===\n")
    
    try:
        # Initialize the manager
        manager = LLMProviderManager()
        
        # Create custom chunking configuration
        config = ChunkingConfig(
            overlap_ratio=0.2,           # 20% overlap for better context
            max_depth=2,                 # Two levels of chunking
            temperature=0.3,             # Slightly more creative
            prefer_fast_models=True,     # Use fast models for efficiency
            include_free_models=False    # Skip free models to avoid rate limits
        )
        
        # Define your summarization prompt
        system_prompt = """
        You are an expert summarizer. Create concise, informative summaries that:
        1. Capture the main points and key insights
        2. Maintain logical flow and coherence
        3. Highlight important details and conclusions
        4. Use clear, professional language
        """
        
        # Perform smart summarization
        result = manager.smart_summarization(long_text, system_prompt, config)
        
        # Display results
        print("=== Processing Summary ===")
        estimates = result['processing_estimates']
        print(f"Original text: {estimates['total_tokens']:,} tokens")
        print(f"Chunks created: {estimates['chunk_count']}")
        print(f"Models used: {', '.join(estimates['models_used'])}")
        print(f"Estimated cost: ${estimates['estimated_cost_usd']:.4f}")
        print(f"Processing time: {estimates['estimated_time_seconds']:.1f} seconds")
        
        print(f"\n=== Final Summary ===")
        print(result['final_summary'])
        
        print(f"\n=== Processing Details ===")
        for level_key, level_results in result['level_results'].items():
            if level_key != 'level_0':  # Skip original text level
                successful = sum(1 for r in level_results if r['success'])
                total = len(level_results)
                print(f"{level_key}: {successful}/{total} chunks processed successfully")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def example_custom_configurations():
    """Show different configuration options"""
    
    print("\n=== Configuration Examples ===\n")
    
    # Configuration for speed (fast processing, minimal overlap)
    speed_config = ChunkingConfig(
        overlap_ratio=0.1,           # Minimal overlap
        max_depth=2,                 # Simple chunking
        temperature=0.1,             # Focused output
        prefer_fast_models=True,     # Use fastest models
        include_free_models=False
    )
    print("Speed-optimized config:", speed_config)
    
    # Configuration for quality (high overlap, deeper analysis)
    quality_config = ChunkingConfig(
        overlap_ratio=0.25,          # High overlap
        max_depth=3,                 # Deeper chunking
        temperature=0.3,             # More nuanced output
        prefer_fast_models=False,    # Use best models
        include_free_models=False
    )
    print("Quality-optimized config:", quality_config)
    
    # Configuration for cost-effectiveness (includes free models)
    budget_config = ChunkingConfig(
        overlap_ratio=0.15,          # Standard overlap
        max_depth=2,                 # Standard depth
        temperature=0.2,             # Balanced creativity
        prefer_fast_models=True,     # Prefer efficient models
        include_free_models=True     # Include free models
    )
    print("Budget-friendly config:", budget_config)

def example_manual_chunking():
    """Example of manual chunking control"""
    
    print("\n=== Manual Chunking Example ===\n")
    
    sample_text = "Your text content here..." * 100
    
    try:
        manager = LLMProviderManager()
        available_models = manager.get_available_models_for_cycling()
        
        if not available_models:
            print("No models available")
            return
        
        # Create overlapping chunks manually
        chunks = manager.create_overlapping_chunks(
            sample_text, 
            available_models[0], 
            overlap_ratio=0.2
        )
        
        print(f"Created {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks[:3]):  # Show first 3
            print(f"  Chunk {i+1}: {chunk['estimated_tokens']} tokens")
            print(f"    Overlaps: prev={chunk['overlap_with_previous']}, next={chunk['overlap_with_next']}")
        
        # Process chunks with cycling
        system_prompt = "Summarize this text chunk concisely."
        results = manager.process_chunks_with_cycling(
            chunks[:3],  # Process first 3 chunks
            system_prompt,
            available_models[:2]  # Use top 2 models
        )
        
        print(f"\nProcessing results:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} Chunk {result['chunk_index']+1}: {result['model_used']}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    example_basic_usage()
    example_custom_configurations()
    example_manual_chunking()