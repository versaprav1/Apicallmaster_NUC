import sys
import sys
print("PYTHONPATH:", sys.path)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os
import json
import streamlit as st
from llm_providers import LLMProviderManager
from dotenv import load_dotenv
load_dotenv()

def load_all_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

import hashlib
from datetime import datetime
import importlib
from types import ModuleType

# Move all UI elements to main() function to avoid duplicates
def extract_text_from_pdfs(docs_dir):
    docs_text = []
    for pdf_file in Path(docs_dir).glob("WIC*.pdf"):
        if PyPDF2:
            try:
                with open(pdf_file, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    docs_text.append(f"--- {pdf_file.name} ---\n{text}")
            except Exception as e:
                docs_text.append(f"[Error reading {pdf_file.name}: {e}]")
        else:
            docs_text.append(f"[PyPDF2 not installed: {pdf_file.name}]")
    return "\n\n".join(docs_text)

def chunk_data(data, chunk_size=100):
    for i in range(0, len(data), chunk_size):
        yield data[i:i+chunk_size]

def get_data_hash(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

def model_rank(model):
    # Define your own ranking of models (higher is better)
    ranks = {
        "gpt-4o": 5,
        "gpt-4o-mini": 4,
        "claude-3-5-sonnet-20241022": 3,
        "gemini-2.5-pro": 2,
        "llama-3.3-70b-versatile": 1,
        "llama-3.1-8b-instant": 0,
        "deepseek/deepseek-chat": 0,
        "meta-llama/llama-3.1-405b-instruct": 0,
    }
    return ranks.get(model, 0)

def load_methods():
    methods_dir = Path(__file__).resolve().parent.parent / "methods"
    # Add methods directory to Python path
    if str(methods_dir.parent) not in sys.path:
        sys.path.insert(0, str(methods_dir.parent))
    
    method_files = [f for f in os.listdir(methods_dir) if f.endswith(".py") and not f.startswith("__")]
    registry = {}
    for fname in method_files:
        modname = fname[:-3]
        try:
            module = importlib.import_module(f"methods.{modname}")
            run_fn = getattr(module, "run", None)
            doc = module.__doc__ or "No description."
            if run_fn:
                registry[modname] = {"run": run_fn, "doc": doc}
        except ImportError as e:
            st.warning(f"Could not import method {modname}: {e}")
            continue
    return registry

def main():
    st.title("Offline WIC Data Q&A Test App (Prompt Cycling)")
    st.markdown("This app lets you ask questions about your saved WIC API data and documentation using your selected LLM provider and multiple expert prompts.")

    llm_manager = LLMProviderManager()
    available_models = llm_manager.get_available_models(show_all=True)
    if not available_models:
        st.error("No LLM models available. Please set your API keys.")
        return
    model_names = list(available_models.keys())
    selected_model = st.selectbox("Select LLM Model", model_names, key="llm_model_select")
    st.info(f"[DEBUG] Using LLM for chunking: {selected_model}")

    # --- Data Loading ---
    project_root = Path(__file__).resolve().parent.parent
    all_data_path = project_root / "assets" / "attached_assets" / "all_data_1750940968693.json"
    docs_dir = project_root / "assets" / "attached_assets"

    if not all_data_path.exists():
        st.error(f"Data file not found: {all_data_path}")
        st.stop()
    
    all_data = load_all_data(all_data_path)
    wic_docs = extract_text_from_pdfs(docs_dir)
    
    if not PyPDF2:
        st.warning("PyPDF2 is not installed. PDF extraction will not work. Only file names will be shown.")

    user_question = st.text_area("Enter your question:", "List all interfaces related to SAP.", height=80)
    chunk_size = st.slider("Chunk size", min_value=10, max_value=500, value=100, step=10)

    # Use the already loaded data
    data = all_data

    # --- Prompt Templates ---
    PROMPT_TEMPLATES = [
        "Extract all interface names, types, senders, and receivers from this data.",
        "Group all interfaces by their type. For each type, list the interface names and their senders/receivers.",
        "List all interfaces where the sender or receiver is SAP.",
        "Summarize all unique senders and receivers in this data.",
        "For each interface, show all nested items and their inventory details.",
        "List all API products along with their associated proxies and data sources.",
        "Get all service bus topics and their associated resource groups.",
        "Find all systems with their corresponding data sources and proxies.",
        "Show me all inventories created in the last 7 days.",
        "List all inventories with their associated tags.",
        "Show me all connections between systems and their data flow counts.",
        "Find all inventories tagged as 'Critical' with their associated systems.",
        "Show inventory creation trends by month with change frequency.",
        "Analyze data flow patterns with their associated properties and types.",
        "Give me a complete system health overview with inventory and flow metrics."
    ]

    # Load extra prompt templates from custom_examples.json
    try:
        with open("custom_examples.json", "r", encoding="utf-8") as f:
            custom_examples = json.load(f)
        extra_prompts = [ex["question"] for ex in custom_examples.get("examples", []) if "question" in ex]
        # Avoid duplicates
        PROMPT_TEMPLATES += [q for q in extra_prompts if q not in PROMPT_TEMPLATES]
    except Exception as e:
        # If file not found or invalid, skip
        pass

    selected_prompts = st.multiselect("Prompt Templates\nSelect prompt templates to use (or add your own below):", PROMPT_TEMPLATES, default=PROMPT_TEMPLATES[:3], key="inner_prompt_templates")
    custom_prompt = st.text_area("Or enter a custom prompt (optional):", "", key="inner_custom_prompt")
    if custom_prompt.strip():
        selected_prompts.append(custom_prompt.strip())

    method_registry = load_methods()
    method_names = list(method_registry.keys())
    st.markdown("---")
    st.markdown("### Knowledge Processing Methods")
    selected_methods = st.multiselect(
        "Select one or more methods to run (in order):",
        method_names,
        default=method_names[:1],
        key="inner_methods_select"
    )
    method_params = {}
    for m in selected_methods:
        st.markdown(f"**{m}**: {method_registry[m]['doc']}")
        # Show parameter options for each method
        if m == "tree_summarization":
            method_params[m] = {"chunk_size": st.number_input(f"Chunk size for {m}", min_value=1, max_value=1000, value=100)}
        elif m == "vector_rag":
            method_params[m] = {"top_k": st.number_input(f"Top-k for {m}", min_value=1, max_value=20, value=3)}
        elif m == "zep_memory":
            method_params[m] = {
                "mode": st.selectbox(f"Mode for {m}", ["recent", "frequent"], key=f"mode_{m}"),
                "top_k": st.number_input(f"Top-k for {m}", min_value=1, max_value=20, value=3, key=f"topk_{m}")
            }
        else:
            method_params[m] = {}

    if st.button("Run Prompt Cycling and Summarize Knowledge"):
        knowledge_summaries = {}
        data_hash = get_data_hash(all_data)
        timestamp = datetime.now().isoformat()
        # Use only the selected model instead of cycling through all models
        for prompt_id, prompt_template in enumerate(selected_prompts):
            st.markdown(f"#### Prompt {prompt_id+1}: {prompt_template}")
            chunk_summaries = []
            chunk_metadata = []
            total_items = len(all_data)
            st.info(f"Processing {total_items} items in chunks of {chunk_size} for this prompt...")
            progress_bar = st.progress(0.0)
            for i, chunk in enumerate(chunk_data(all_data, chunk_size)):
                chunk_text = json.dumps(chunk)[:2000]
                prompt = (
                    f"TASK: {prompt_template}\n\n"
                    f"DATA TO ANALYZE:\n{chunk_text}\n\n"
                    f"INSTRUCTIONS: Perform ONLY the task specified above. Do not assume what the user wants. Do not default to listing SAP interfaces unless the task specifically asks for that. Focus on the exact requirements of the task."
                )
                summary = None
                used_model = None
                error = None
                
                # Try the selected model first, with fallback to other models only for rate limits
                models_to_try = [selected_model] + [m for m in model_names if m != selected_model]
                for model_try in models_to_try:
                    st.write(f"[DEBUG] Trying chunk {i+1} with {model_try}...")
                    try:
                        result = llm_manager.generate_response(
                            model_try,
                            "You are an expert data analyst. Follow the specific task instructions exactly as provided. Do not make assumptions about what the user wants - only do exactly what the task asks for.",
                            prompt,
                            temperature=0.1,
                            max_tokens=2048
                        )
                        if result and isinstance(result, str) and len(result.strip()) > 0:
                            summary = result
                            used_model = model_try
                            st.write(f"[DEBUG] ✅ Success with {model_try}")
                            break
                        else:
                            error = f"Empty or invalid response from {model_try}"
                            st.write(f"[DEBUG] ❌ Failed with {model_try}: {error}")
                    except Exception as e:
                        error = str(e)
                        st.write(f"[DEBUG] ❌ Exception with {model_try}: {error}")
                        if "rate limit" not in error.lower() and "429" not in error:
                            break  # Only cycle for rate limit errors
                if summary:
                    chunk_summaries.append(summary)
                    chunk_metadata.append({
                        "model": used_model,
                        "timestamp": timestamp,
                        "data_hash": get_data_hash(chunk),
                        "status": "success"
                    })
                else:
                    chunk_summaries.append(error or "Error: Unknown")
                    chunk_metadata.append({
                        "model": used_model or model_names[0],
                        "timestamp": timestamp,
                        "data_hash": get_data_hash(chunk),
                        "status": "error",
                        "error": error
                    })
                progress = (i+1) * chunk_size / total_items
                progress_bar.progress(min(progress, 1.0))
            # Aggregate only if at least one chunk succeeded
            if any(m["status"] == "success" for m in chunk_metadata):
                final_prompt = (
                    f"Task: {prompt_template}\n\n"
                    f"Here are summaries from all data chunks:\n{json.dumps(chunk_summaries)}\n\n"
                    f"Please provide a comprehensive final answer that addresses the task above based on these chunk summaries. "
                    f"Focus specifically on what the task is asking for, not on any other topics."
                )
                final_answer = None
                used_model = None
                error = None
                
                # Use the same model selection logic for final aggregation
                models_to_try = [selected_model] + [m for m in model_names if m != selected_model]
                for model_try in models_to_try:
                    st.write(f"[DEBUG] Aggregating final answer for prompt {prompt_id+1} with {model_try}...")
                    try:
                        result = llm_manager.generate_response(
                            model_try,
                            "You are an expert data analyst. Follow the specific task instructions exactly as provided. Synthesize the chunk summaries to answer only what the task asks for.",
                            final_prompt,
                            temperature=0.1,
                            max_tokens=2048
                        )
                        if not (isinstance(result, str) and result.strip().lower().startswith("error: ")):
                            final_answer = result
                            used_model = model_try
                            break
                        else:
                            error = result
                    except Exception as e:
                        error = str(e)
                        if "rate limit" not in error.lower() and "429" not in error:
                            break
                st.markdown(f"**Final Answer for Prompt {prompt_id+1}:**")
                if final_answer:
                    st.markdown(final_answer)
                else:
                    st.error(f"Final answer failed: {error}")
            else:
                final_answer = None
                used_model = None
                st.error("All chunks failed for this prompt. No final answer generated.")
            with st.expander(f"Show all chunk summaries for Prompt {prompt_id+1}"):
                for idx, (summary, meta) in enumerate(zip(chunk_summaries, chunk_metadata), 1):
                    st.markdown(f"**Chunk {idx}** (model: {meta['model']}, status: {meta['status']}, time: {meta['timestamp']}):\n{summary}")
            # Save knowledge summary with metadata and history
            summary_path = project_root / f"test/knowledge_summary_prompt_{prompt_id+1}.json"
            prev_summary = None
            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    prev_summary = json.load(f)
            history = prev_summary.get("history", []) if prev_summary else []
            # Only update if new is better or previous was error or data changed
            should_update = True
            if prev_summary:
                prev_model = prev_summary.get("model")
                prev_status = prev_summary.get("status", "success")
                prev_data_hash = prev_summary.get("data_hash")
                if prev_status == "success" and final_answer and model_rank(used_model) <= model_rank(prev_model) and data_hash == prev_data_hash:
                    should_update = False
            if should_update and final_answer:
                if prev_summary:
                    history.append({k: v for k, v in prev_summary.items() if k != "history"})
                knowledge_summaries[f"prompt_{prompt_id+1}"] = {
                    "prompt": prompt_template,
                    "final_answer": final_answer,
                    "chunk_summaries": chunk_summaries,
                    "chunk_metadata": chunk_metadata,
                    "model": used_model,
                    "timestamp": timestamp,
                    "data_hash": data_hash,
                    "status": "success",
                    "history": history
                }
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(knowledge_summaries[f"prompt_{prompt_id+1}"], f, indent=2)
            elif prev_summary:
                st.info("No update: previous summary is as good or better and data unchanged.")
        st.success("All prompts processed and knowledge summaries saved.")

    # --- Run Pipeline ---
    if st.button("Run Knowledge Pipeline"):
        st.info(f"Running pipeline: {selected_methods}")
        context = data
        summaries_file = None
        for method in selected_methods:
            method_path = Path(__file__).resolve().parent.parent / "methods" / f"{method}.py"
            if not method_path.exists():
                st.error(f"Method {method} not found.")
                continue
            module = importlib.import_module(f"methods.{method}")
            run_fn = getattr(module, "run", None)
            if not callable(run_fn):
                st.error(f"No run() function in {method}.")
                continue
            st.write(f"Running {method}...")
            if method == "db_lookup":
                # Improved field mapping: pass all prompts and data
                result, meta = run_fn(query=None, data=context, prompt_templates=selected_prompts)
                summaries_file = meta.get("summary_file")
                st.write("Per-prompt summaries:")
                for p, s in result.items():
                    st.markdown(f"**Prompt:** {p}")
                    st.code(s)
            elif method == "llm_synthesis":
                if not summaries_file:
                    st.warning("No summaries file from db_lookup; skipping llm_synthesis.")
                    continue
                # Pass llm_manager and selected model to llm_synthesis
                result, meta = run_fn(query=None, data=None, prompt_templates=selected_prompts, summaries_file=summaries_file, llm_model=selected_model, llm_manager=llm_manager)
                st.write("Final LLM Synthesis Result:")
                st.code(result)
                st.write("Provenance:")
                st.json(meta)
            else:
                # For other methods, just pass data and prompts
                result, meta = run_fn(query=None, data=context, prompt_templates=selected_prompts)
                st.write(f"Result from {method}:")
                st.code(result)
                st.write("Metadata:")
                st.json(meta)
            # Pass along context if needed (for chaining)
            context = result

if __name__ == "__main__":
    main() 