from typing import Any, Dict, Iterator, List, Optional, Tuple
try:
    # Prefer importing via src as app.py uses src.* modules
    from src.inventory_types import INVENTORY_TYPES  # type: ignore
except Exception:
    # Fallback if src not on path
    INVENTORY_TYPES = {}


def _value_includes(haystack: Any, needle: str) -> bool:
    try:
        return needle.lower() in str(haystack).lower()
    except Exception:
        return False


def _test_operator(field_value: Any, op: str, value: Any) -> bool:
    try:
        if op == "eq":
            return str(field_value) == str(value)
        if op == "ne":
            return str(field_value) != str(value)
        if op == "like":
            return _value_includes(field_value, str(value))
        # Numeric comparisons
        fv = float(field_value) if field_value is not None else None
        vv = float(value) if value is not None else None
        if fv is None or vv is None:
            return False
        if op == "gt":
            return fv > vv
        if op == "lt":
            return fv < vv
        if op == "gte":
            return fv >= vv
        if op == "lte":
            return fv <= vv
    except Exception:
        return False
    return False


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _get_type_field(item: Dict[str, Any]) -> Any:
    """Return the type value from common locations (top-level or nested)."""
    v = _get_nested(item, "type")
    if v is not None:
        return v
    return _get_nested(item, "inventory.type")


def _invert_inventory_types() -> Dict[str, str]:
    inv: Dict[str, str] = {}
    if isinstance(INVENTORY_TYPES, dict):
        for k, v in INVENTORY_TYPES.items():
            inv[str(v).strip().lower()] = str(k)
    return inv


_INVERTED_TYPES = _invert_inventory_types()


def resolve_inventory_type_filter(op: str, value: Any) -> Tuple[str, Any]:
    """Normalize inventory type filters to numeric IDs.

    Accepts numeric strings, integers, canonical labels (e.g., 'MULE_APP'), and group shorthands
    such as 'MULE', 'SAP', 'AZURE', 'APIM', 'OTHER', 'BACKEND', 'EAM'. Returns a tuple of (op, value)
    where value is normalized to ID(s) as strings.
    """
    group_map = {
        "mule": ["0", "1"],
        "sap": ["14", "15", "16", "17", "18", "19", "20"],
        "azure": ["3", "4", "5", "6", "7", "8"],
        "apim": ["2"],
        "other": ["9", "10", "11", "12", "13", "21"],
        "backend": ["9", "10", "11", "12", "13", "21"],
        "eam": ["21"],
    }

    def normalize_one(x: Any) -> List[str]:
        s = str(x).strip()
        # Numeric id as-is
        if s.isdigit():
            return [s]
        key = s.lower()
        # Group shorthand
        if key in group_map:
            return group_map[key]
        # Canonical label -> id via INVENTORY_TYPES inversion
        if key in _INVERTED_TYPES:
            return [_INVERTED_TYPES[key]]
        # Unknown; return as-is to avoid over-filtering
        return [s]

    if op == "in" and isinstance(value, list):
        out: List[str] = []
        for v in value:
            out.extend(normalize_one(v))
        # de-duplicate
        return op, sorted(list({x for x in out}))
    else:
        # eq or others
        ids = normalize_one(value)
        if op == "eq" and len(ids) > 1:
            # Expand eq on a group into an 'in'
            return "in", ids
        return op, ids[0] if len(ids) == 1 else ids


def _match_condition(item: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    # field condition
    if 'field' in cond and isinstance(cond['field'], dict):
        field = cond['field']
        name = field.get('name')
        if not name:
            return False
        value = None
        op = None
        for k in ('eq','ne','like','gt','lt','gte','lte','in'):
            if k in field:
                op = k
                value = field[k]
                break
        # Special handling for inventory type field
        if name == 'type':
            # Normalize operator/value and read from common locations
            op, value = resolve_inventory_type_filter(op or 'eq', value)
            actual = _get_type_field(item)
            if op == 'in' and isinstance(value, list):
                # Compare using normalized string ids
                try:
                    actual_s = str(actual)
                except Exception:
                    actual_s = ""
                ok = actual_s in [str(x) for x in value]
            else:
                ok = _test_operator(actual, op or 'eq', value)
            if cond.get('not'):
                return not ok
            return ok
        # General case
        actual = _get_nested(item, name)
        ok = _test_operator(actual, op or 'eq', value)
        if cond.get('not'):
            return not ok
        return ok
    # entity predicate (nested)
    if 'entity' in cond and isinstance(cond['entity'], dict):
        entity_block = cond['entity']
        preds = entity_block.get('predicates', [])
        # For local JSON, we interpret predicates as further conditions applied to same item with dotted paths
        # e.g., sender.data_source_id like "X"
        inner_ok = True
        for p in preds:
            for inner in p.get('conditions', []):
                # Map to nested path by prefixing entity name
                if 'field' in inner and 'name' in inner['field'] and isinstance(inner['field']['name'], str):
                    inner['field']['name'] = f"{entity_block.get('name', '').strip()}.{inner['field']['name']}"
                if not _match_condition(item, inner):
                    inner_ok = False
                    break
            if not inner_ok:
                break
        return inner_ok
    return False


def _match_condition_group(item: Dict[str, Any], group: Dict[str, Any]) -> bool:
    option = int(group.get('option', 0))  # 0=AND, 1=OR
    conditions = group.get('conditions', [])
    if option == 1:
        return any(_match_condition(item, c) for c in conditions)
    return all(_match_condition(item, c) for c in conditions)


def filter_records(records: Iterator[Dict[str, Any]], where: List[Dict[str, Any]] | None) -> Iterator[Dict[str, Any]]:
    if not where:
        for r in records:
            yield r
        return
    for r in records:
        ok = all(_match_condition_group(r, g) for g in where)
        if ok:
            yield r


def project_fields(item: Dict[str, Any], fields: List[str] | None) -> Dict[str, Any]:
    if not fields:
        return item
    out: Dict[str, Any] = {}
    for f in fields:
        if '.' in f:
            # Support dotted fields: a.b
            val = _get_nested(item, f)
            out[f] = val
        else:
            if f in item:
                out[f] = item[f]
    return out


def include_with(item: Dict[str, Any], with_blocks: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    if not with_blocks:
        return item
    out = dict(item)
    for w in with_blocks:
        name = w.get('entity') if isinstance(w, dict) else None
        if not name:
            continue
        # In local JSON, related data is typically embedded; pass through if present
        ent_name = name if isinstance(name, str) else name.get('name')
        if isinstance(ent_name, str) and ent_name in item:
            out[ent_name] = item.get(ent_name)
        # If fields specified for the with-entity, project them
        fields = w.get('fields') if isinstance(w, dict) else None
        if fields and isinstance(out.get(ent_name), dict):
            sub = out.get(ent_name, {})
            out[ent_name] = {k: sub.get(k) for k in fields if k in sub}
    return out


def execute_query(records: Iterator[Dict[str, Any]], query: Dict[str, Any]) -> List[Dict[str, Any]]:
    q = query.get('query', {}) if 'query' in query else {}
    fields = q.get('fields') if isinstance(q.get('fields'), list) else None
    where = q.get('where') if isinstance(q.get('where'), list) else None
    with_blocks = q.get('with') if isinstance(q.get('with'), list) else None
    limit = int(q.get('limit', 100))
    offset = int(q.get('offset', 0))

    results: List[Dict[str, Any]] = []
    skipped = 0
    for item in filter_records(records, where):
        if skipped < offset:
            skipped += 1
            continue
        projected = project_fields(item, fields)
        enriched = include_with(projected, with_blocks)
        results.append(enriched)
        if len(results) >= limit:
            break
    return results


