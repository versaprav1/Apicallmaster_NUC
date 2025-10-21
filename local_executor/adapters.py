from typing import Any, Dict, List


def to_api_response(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a response object shaped like the live API returns.
    Minimal contract: a dict with 'data': list.
    """
    return {"data": items}


