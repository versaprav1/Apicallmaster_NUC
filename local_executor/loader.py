import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional


def _iter_json_array(file_path: Path) -> Iterator[Any]:
    """Yield items from a large JSON array.
    Tries ijson for streaming; falls back to stdlib json.load when unavailable.
    """
    try:
        import ijson  # type: ignore
        with file_path.open("rb") as f:
            for item in ijson.items(f, "item"):
                yield item
        return
    except Exception:
        pass
    # Fallback: load whole file (may be memory heavy for very large files)
    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
        if isinstance(data, list):
            for item in data:
                yield item
        elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                yield item


def iter_records(file_path: str) -> Iterator[Any]:
    """Detect file type and iterate records uniformly.
    Supports one JSON array or an object with 'data': [...].
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(str(file_path))
    yield from _iter_json_array(path)


