"""
DB lookup method: field-based search and summarization for each prompt.
"""
import json
from pathlib import Path
import hashlib

def get_data_hash(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

def run(query, data, prompt_templates=None, save_dir="knowledge_summaries", **kwargs):
    """
    For each prompt, search relevant fields in data, summarize, and save results.
    Args:
        query: The user query or prompt (not used here, see prompt_templates).
        data: List of dicts (your knowledge base).
        prompt_templates: List of prompts to process.
        save_dir: Directory to save summaries.
    Returns:
        summaries: Dict of {prompt: summary}.
        meta: Metadata about the process.
    """
    # Field mapping for each prompt (customize as needed)
    field_map = {
        "List all interfaces related to SAP.": ["interface_name", "sender", "receiver"],
        "Extract all interface names, types, senders, and receivers from this data.": ["interface_name", "type", "sender", "receiver"],
        "Group all interfaces by their type. For each type, list the interface names and their senders/receivers.": ["type", "interface_name", "sender", "receiver"],
        "List all interfaces where the sender or receiver is SAP.": ["sender", "receiver"],
        "Summarize all unique senders and receivers in this data.": ["sender", "receiver"],
        "For each interface, show all nested items and their inventory details.": ["interface_name", "inventory"],
        # Add more prompt-to-field mappings as needed
    }
    # Default: search all fields
    all_fields = set()
    for item in data:
        all_fields.update(item.keys())
    
    summaries = {}
    data_hash = get_data_hash(data)
    Path(save_dir).mkdir(exist_ok=True)
    for prompt in (prompt_templates or []):
        fields = field_map.get(prompt, list(all_fields))
        # Simple search: include item if any field contains a keyword from the prompt
        keywords = [w.lower() for w in prompt.split() if len(w) > 2]
        results = []
        for item in data:
            for f in fields:
                val = str(item.get(f, "")).lower()
                if any(k in val for k in keywords):
                    results.append(item)
                    break
        # Summarize results
        if results:
            summary = f"Found {len(results)} items for prompt: '{prompt}'.\nSample: {json.dumps(results[:3], indent=2)}"
        else:
            summary = f"No results found for prompt: '{prompt}'."
        summaries[prompt] = summary
    # Save summaries
    out_path = Path(save_dir) / f"db_lookup_{data_hash}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)
    meta = {"method": "db_lookup", "data_hash": data_hash, "summary_file": str(out_path)}
    return summaries, meta 