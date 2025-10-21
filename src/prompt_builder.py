"""
Prompt Builder Utilities

This module centralizes construction of provider-agnostic system prompts
for two primary purposes:
  1) Translation: Convert natural language to WHINT Integration Cockpit JSON queries
  2) Synthesis: Summarize and synthesize multiple chunks/answers

It pulls dynamic context from existing, authoritative sources in the repo:
  - inventory_types.INVENTORY_TYPES
  - Optional: ApiCallMaster/all_interface_names.txt (sample grounding)
  - Optional: knowledge_cache/*.json summaries if present (future extension)

No provider SDKs are imported here; the output is plain strings so callers can
use them with any LLM provider (OpenAI, Anthropic, Gemini, Groq, etc.).
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


# Local imports are relative to ApiCallMaster/src
try:
    from inventory_types import INVENTORY_TYPES
except Exception:
    INVENTORY_TYPES = {}


REPO_ROOT = Path(__file__).resolve().parents[2]
APICALLMASTER_ROOT = REPO_ROOT / "ApiCallMaster"
ALL_INTERFACE_NAMES_PATH = APICALLMASTER_ROOT / "all_interface_names.txt"


def _load_sample_interface_names(max_count: int = 10) -> List[str]:
    """Load a small, rotating sample of interface names for grounding.

    Tries to read ApiCallMaster/all_interface_names.txt if present. Falls back
    to an empty list if not available. The goal is to add realistic examples
    without bloating the prompt.
    """
    names: List[str] = []
    try:
        if ALL_INTERFACE_NAMES_PATH.exists():
            with ALL_INTERFACE_NAMES_PATH.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    value = line.strip()
                    if value:
                        names.append(value)
                        if len(names) >= max_count:
                            break
    except Exception:
        # Non-fatal; simply return empty sample
        return []
    return names


def _format_inventory_types_map() -> str:
    """Return a compact, readable inventory type table as text for prompts."""
    if not isinstance(INVENTORY_TYPES, dict) or not INVENTORY_TYPES:
        return "(inventory types unavailable)"
    pairs: List[str] = []
    for type_id, name in INVENTORY_TYPES.items():
        pairs.append(f"{type_id}={name}")
    return ", ".join(pairs)


def _routing_guidance() -> str:
    """Routing rules guidance text for the prompt."""
    return (
        "Routing by type: SAP → /sap, MULE → /mule, AZURE → /azure, APIM → /apim, "
        "mixed/general or OTHER/BACKEND/EAM → /interfaces. Use 'in' for multiple types, 'eq' for single type."
    )


def build_system_prompt_translation(
    persona: Optional[str] = None,
    include_examples: bool = True,
    sample_interface_count: int = 8,
) -> str:
    """Construct the system prompt for NL → WHINT query translation.

    Args:
        persona: Optional custom role/voice for the assistant.
        include_examples: Whether to include minimal working examples.
        sample_interface_count: How many interface names to include for grounding.

    Returns:
        A system prompt string suitable for provider-agnostic use.
    """
    persona_text = (
        persona
        or "You are an expert at creating WHINT Integration Cockpit API queries from natural language."
    )

    inventory_map = _format_inventory_types_map()
    sample_names = _load_sample_interface_names(max_count=sample_interface_count)

    examples_block = ""
    if include_examples:
        examples_block = (
            "\nMinimal examples (structure only, adapt values to the user request):\n"
            "1) Search by name:\n"
            "{\n  \"query\": {\n    \"entity\": \"inventory\",\n    \"fields\": [\"name\", \"sender_name\", \"receiver_name\", \"description\", \"type\"],\n    \"where\": [{\n      \"option\": 1,\n      \"conditions\": [{\n        \"field\": {\n          \"name\": \"name\",\n          \"like\": \"Connect\"\n        }\n      }]\n    }],\n    \"limit\": 300,\n    \"offset\": 0\n  }\n}\n"
            "2) List ALL interfaces (no limit for complete results):\n"
            "{\n  \"query\": {\n    \"entity\": \"inventory\",\n    \"fields\": [\"name\", \"sender_name\", \"receiver_name\", \"description\", \"type\"]\n  }\n}\n"
            "3) SAP interfaces (type filter with in):\n"
            "{\n  \"query\": {\n    \"entity\": \"inventory\",\n    \"fields\": [\"name\", \"sender_name\", \"receiver_name\", \"description\", \"type\"],\n    \"where\": [{\n      \"option\": 1,\n      \"conditions\": [{\n        \"field\": {\n          \"name\": \"type\",\n          \"in\": [\"14\", \"15\", \"16\", \"17\", \"18\", \"19\", \"20\"]\n        }\n      }]\n    }],\n    \"limit\": 300\n  }\n}\n"
            "4) Tasks with failed runs:\n"
            "{\n  \"query\": {\n    \"entity\": \"task\",\n    \"fields\": [],\n    \"with\": [{\n      \"entity\": \"runs\",\n      \"where\": [{\n        \"option\": 1,\n        \"conditions\": [{\n          \"field\": {\n            \"name\": \"successful\",\n            \"eq\": \"false\"\n          }\n        }]\n      }]\n    }]\n  }\n}\n"
        )

    sample_names_block = ""
    if sample_names:
        # Keep this concise to avoid token bloat
        sample_names_block = (
            "\nRepresentative interface names (for grounding only; do not echo unless needed):\n"
            + ", ".join(sample_names)
            + "\n"
        )

    sections: List[str] = [
        f"{persona_text}",
        "\nObjectives:",
        "- Convert user requests into precise WHINT JSON queries.",
        "- Prefer targeted queries: include relevant fields and appropriate filters.",
        "- Enforce valid structure and operators; avoid extraneous text.",
        "\nEntities: inventory, task, datasource, dataFlow, system, logEntry",
        "Operators: eq, like, ne, gt, lt, gte, lte",
        f"Inventory Types (id=name): {inventory_map}",
        f"{_routing_guidance()}",
        sample_names_block,
        "\nStructure rules:",
        "- Read: {\"query\": {\"entity\": \"...\", \"fields\": [...], \"where\": [...], \"with\": [...], \"limit\": N, \"offset\": M}}",
        "- Where groups use {\"option\": 0} for AND, {\"option\": 1} for OR",
        "- Field filter: {\"field\": {\"name\": \"fieldname\", \"<op>\": \"value\"}}",
        "- Nested entity filter: {\"entity\": {\"name\": \"entityname\", \"predicates\": [...]}}",
        "- Use numeric type IDs in filters",
        examples_block,
        "\nOutput contract:",
        "- Respond with ONLY the JSON structure. No explanations.",
        "- If the request cannot be fulfilled under these rules, return the closest valid JSON that reflects constraints (e.g., narrower fields/limits).",
        "\nValidation checklist before responding:",
        "- Root key is \"query\" (for reads) or \"upsert\" (for writes)",
        "- Valid entity name and allowed operators",
        "- Appropriate routing type filters when the user implies a platform (SAP/MULE/AZURE/APIM)",
        "- Use limit only for specific searches; omit limit for 'all' or 'list all' requests",
    ]

    return "\n".join([s for s in sections if s is not None and len(str(s).strip()) > 0])


def build_system_prompt_synthesis(
    persona: Optional[str] = None,
) -> str:
    """Construct the system prompt for synthesis of multiple summaries/answers.

    Args:
        persona: Optional custom role/voice for the assistant.

    Returns:
        A system prompt string suitable for provider-agnostic use.
    """
    persona_text = (
        persona
        or "You are an expert integration analyst. Synthesize a concise, complete answer from provided summaries."
    )

    sections: List[str] = [
        f"{persona_text}",
        "\nInstructions:",
        "- Integrate all provided per-prompt summaries into one coherent answer.",
        "- Prefer factual correctness and clarity; avoid duplication.",
        "- If summaries conflict, note the discrepancy briefly and choose the most supported claim.",
        "- Keep the tone professional and the structure scannable (short paragraphs, lists where helpful).",
        "- Avoid hallucinations; do not invent data beyond the provided context.",
    ]

    return "\n".join(sections)


__all__ = [
    "build_system_prompt_translation",
    "build_system_prompt_synthesis",
]




