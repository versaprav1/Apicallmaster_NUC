#!/usr/bin/env python3
"""
Demo script for intelligent chunking and model cycling
"""

import sys
import os
sys.path.append('src')

from llm_providers import LLMProviderManager

def demo_chunking_and_cycling():
    """Demonstrate the new chunking and cycling features"""
    
    # Sample long text for testing
    sample_text = """
    Artificial Intelligence (AI) has revolutionized numerous industries and aspects of human life. 
    From healthcare to finance, transportation to entertainment, AI technologies are reshaping how we work, 
    live, and interact with the world around us. Machine learning, a subset of AI, enables computers to 
    learn and improve from experience without being explicitly programmed for every task.
    
    Deep learning, which uses neural networks with multiple layers, has been particularly successful in 
    areas such as image recognition, natural language processing, and speech recognition. These technologies 
    power many of the applications we use daily, from virtual assistants like Siri and Alexa to 
    recommendation systems on streaming platforms and e-commerce websites.
    
    The development of large language models (LLMs) has marked a significant milestone in AI advancement. 
    Models like GPT, BERT, and their successors have demonstrated remarkable capabilities in understanding 
    and generating human-like text. These models are trained on vast amounts of text data and can perform 
    a wide range of language tasks, from translation and summarization to creative writing and code generation.
    
    However, the rapid advancement of AI also brings challenges and considerations. Ethical concerns about 
    bias, privacy, and the potential for misuse of AI technologies are increasingly important. There are 
    ongoing discussions about the need for AI governance, regulation, and ensuring that AI development 
    benefits all of humanity while minimizing potential risks.
    
    The future of AI holds immense promise. Researchers are working on developing more efficient, 
    interpretable, and aligned AI systems. Areas like artificial general intelligence (AGI), quantum 
    computing integration with AI, and AI-human collaboration are at the forefront of current research. 
    As we continue to advance in this field, it's crucial to maintain a balance between innovation and 
    responsible development.
    """ * 5  # Repeat to make it longer for chunking demo
    
    print("=== AI Chunking and Model Cycling Demo ===\n")
    
    try:
        manager = LLMProviderManager()
        
        # Get available models for cycling
        available_models = manager.get_available_models_for_cycling(prefer_fast=True, include_free=False)
        print(f"Available models for cycling: {available_models}\n")
        
        if not available_models:
            print("❌ No models available. Please check your API keys.")
            return
        
        # Estimate processing requirements
        estimates = manager.estimate_processing_time(sample_text, available_models[:3])  # Use top 3 models
        print("=== Processing Estimates ===")
        print(f"Total tokens: {estimates['total_tokens']:,}")
        print(f"Chunks needed: {estimates['chunk_count']}")
        print(f"Estimated time: {estimates['estimated_time_seconds']:.1f} seconds")
        print(f"Estimated cost: ${estimates['estimated_cost_usd']:.4f}")
        print(f"Models to use: {estimates['models_used']}")
        print(f"Chunks per model: {estimates['chunks_per_model']}\n")
        
        # Demo 1: Basic overlapping chunks
        print("=== Demo 1: Overlapping Chunks ===")
        chunks = manager.create_overlapping_chunks(sample_text, available_models[0], overlap_ratio=0.2)
        print(f"Created {len(chunks)} overlapping chunks:")
        for i, chunk in enumerate(chunks[:3]):  # Show first 3
            print(f"  Chunk {i+1}: {chunk['estimated_tokens']} tokens, "
                  f"overlap_prev: {chunk['overlap_with_previous']}, "
                  f"overlap_next: {chunk['overlap_with_next']}")
        print(f"  ... and {len(chunks)-3} more chunks\n")
        
        # Demo 2: Recursive chunking
        print("=== Demo 2: Recursive Chunking ===")
        recursive_chunks = manager.create_recursive_chunks(sample_text, available_models[0], max_depth=2)
        for level, chunks in recursive_chunks.items():
            print(f"  {level}: {len(chunks)} chunks, "
                  f"avg tokens: {sum(c['estimated_tokens'] for c in chunks) / len(chunks):.0f}")
        print()
        
        # Demo 3: Process with model cycling (just first few chunks to avoid API costs)
        print("=== Demo 3: Model Cycling Processing ===")
        test_chunks = chunks[:3]  # Just process first 3 chunks for demo
        system_prompt = "Summarize the following text chunk concisely, focusing on key points about AI."
        
        results = manager.process_chunks_with_cycling(
            test_chunks, system_prompt, available_models[:2], temperature=0.3
        )
        
        print("Processing results:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            model = result['model_used']
            tokens = result['input_tokens']
            print(f"  {status} Chunk {result['chunk_index']+1}: {model} ({tokens} tokens)")
            if result['success']:
                preview = result['response'][:100] + "..." if len(result['response']) > 100 else result['response']
                print(f"      Preview: {preview}")
        print()
        
        # Demo 4: Full recursive summarization (with limited depth to save API calls)
        print("=== Demo 4: Recursive Summarization ===")
        print("Note: Using smaller text sample to demonstrate without excessive API calls")
        
        small_sample = sample_text[:2000]  # Smaller sample for demo
        summary_result = manager.recursive_summarization(
            small_sample, 
            "Create a concise summary focusing on the main points about AI development and challenges.",
            available_models[:2],  # Use top 2 models
            max_depth=2,
            overlap_ratio=0.15
        )
        
        print(f"Recursive summarization completed:")
        print(f"  Original tokens: {summary_result['original_text_tokens']}")
        print(f"  Levels processed: {summary_result['levels_processed']}")
        print(f"  Final summary length: {len(summary_result['final_summary'])} chars")
        print(f"  Final summary preview: {summary_result['final_summary'][:200]}...")
        
    except Exception as e:
        print(f"❌ Error in demo: {str(e)}")

def show_chunking_options():
    """Show available chunking configuration options"""
    print("\n=== Chunking Configuration Options ===")
    print("""
1. OVERLAP RATIO (0.1 - 0.3 recommended):
   - 0.1 (10%): Minimal overlap, faster processing
   - 0.15 (15%): Balanced overlap, good for most cases
   - 0.2 (20%): High overlap, better context preservation
   - 0.3 (30%): Maximum overlap, best for complex analysis

2. MAX DEPTH for recursive chunking (1-4 recommended):
   - 1: Single level chunking
   - 2: Two-level hierarchy (recommended for most cases)
   - 3: Three levels (for very large documents)
   - 4+: Deep hierarchy (rarely needed)

3. MODEL CYCLING STRATEGIES:
   - prefer_fast=True: Prioritize speed (GPT-4o-mini, Groq models)
   - prefer_fast=False: Prioritize capability (larger models first)
   - include_free=True: Include free models (may hit rate limits)
   - include_free=False: Skip free models (more reliable)

4. CHUNK SIZE OPTIMIZATION:
   - Automatically adjusts based on model context length
   - Uses 70% of context for chunk, 30% for prompt/response
   - Tries to break at sentence boundaries

5. TEMPERATURE SETTINGS:
   - 0.1: Very focused, consistent summaries
   - 0.3: Balanced creativity and consistency
   - 0.7: More creative, varied outputs
    """)

if __name__ == "__main__":
    demo_chunking_and_cycling()
    show_chunking_options()