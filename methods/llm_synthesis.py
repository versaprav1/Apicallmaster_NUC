"""
LLM synthesis method: synthesize a comprehensive answer from per-prompt summaries using LLM.
"""
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from llm_providers import LLMProviderManager
from prompt_builder import build_system_prompt_synthesis

def run(query, data, prompt_templates=None, summaries_file=None, llm_model=None, llm_manager=None, save_dir="knowledge_summaries", **kwargs):
    """
    Loads per-prompt summaries, synthesizes a final answer using LLM.
    Args:
        query: The user query (not used, see prompt_templates).
        data: Not used (summaries are loaded from file).
        prompt_templates: List of prompts (for provenance).
        summaries_file: Path to per-prompt summaries JSON.
        llm_model: Preferred LLM model.
        save_dir: Directory to save final summary.
    Returns:
        final_summary: The LLM's synthesized answer.
        meta: Metadata about the process.
    """
    # Load per-prompt summaries
    if not summaries_file:
        raise ValueError("summaries_file must be provided")
    with open(summaries_file, "r", encoding="utf-8") as f:
        summaries = json.load(f)
    # Concatenate summaries
    context = "\n\n".join([f"Prompt: {p}\nSummary: {s}" for p, s in summaries.items()])
    
    # Use provided llm_manager or create a new one
    if llm_manager is None:
        llm_manager = LLMProviderManager()
    
    # Use provided model or get the best available one
    if llm_model is None:
        available_models = llm_manager.get_available_models(show_all=False)
        if not available_models:
            raise ValueError("No LLM models available. Please set your API keys.")
        llm_model = list(available_models.keys())[0]  # Use first available model
    
    system_prompt = build_system_prompt_synthesis()
    user_prompt = context
    
    try:
        answer = llm_manager.generate_response(
            llm_model,
            system_prompt,
            user_prompt,
            temperature=0.1,
            max_tokens=4096
        )
    except Exception as e:
        raise Exception(f"Error generating LLM synthesis: {str(e)}")
    
    # Save final summary
    data_hash = summaries_file.split("_")[-1].split(".")[0] if "_" in summaries_file else "unknown"
    Path(save_dir).mkdir(exist_ok=True)
    out_path = Path(save_dir) / f"llm_synthesis_{data_hash}.json"
    result = {
        "final_summary": answer,
        "timestamp": datetime.utcnow().isoformat(),
        "llm_model": llm_model,
        "provenance": {
            "summaries_file": summaries_file,
            "prompt_templates": prompt_templates,
        },
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    meta = {"method": "llm_synthesis", "summary_file": str(out_path)}
    return answer, meta 