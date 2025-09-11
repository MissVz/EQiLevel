import os
import csv
from typing import List, Dict, Optional

_CACHE: List[Dict] | None = None

def _csv_path() -> str:
    here = os.path.dirname(os.path.dirname(__file__))  # app/
    return os.path.join(here, 'db', 'objectives.csv')

def _load() -> List[Dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = _csv_path()
    rows: List[Dict] = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            r = csv.DictReader(f)
            for row in r:
                # normalize/strip
                obj = {k: (v.strip() if isinstance(v, str) else v) for k,v in row.items()}
                rows.append(obj)
    except FileNotFoundError:
        rows = []
    _CACHE = rows
    return rows

def list_objectives(unit: Optional[str] = None, q: Optional[str] = None) -> List[Dict]:
    rows = _load()
    out = rows
    if unit:
        out = [r for r in out if r.get('unit','').lower() == unit.lower()]
    if q:
        ql = q.lower()
        out = [r for r in out if ql in (r.get('objective_code','') + ' ' + r.get('description','')).lower()]
    return out

def find_by_code(code: str) -> Optional[Dict]:
    if not code:
        return None
    code = code.strip().lower()
    for r in _load():
        if r.get('objective_code','').strip().lower() == code:
            return r
    return None

def format_for_prompt(objs: List[Dict], max_items: int = 3) -> str:
    """Return a compact string suitable for a system prompt."""
    if not objs:
        return ''
    items = []
    for o in objs[:max_items]:
        code = o.get('objective_code','').strip()
        desc = o.get('description','').strip()
        strands = o.get('strands','').strip()
        prereq = o.get('prereqs','').strip()
        examples = o.get('examples','').strip()
        mastery = o.get('mastery_threshold','').strip()
        assess = o.get('assessment_types','').strip()
        parts = [f"{code}: {desc}"]
        if strands:
            parts.append(f"strands={strands}")
        if prereq:
            parts.append(f"prereqs={prereq}")
        if examples:
            parts.append(f"examples={examples}")
        if mastery:
            parts.append(f"mastery_threshold={mastery}")
        if assess:
            parts.append(f"assessment_types={assess}")
        items.append(' • ' + '; '.join(parts))
    return "\nCurriculum objectives:\n" + "\n".join(items) + "\nUse these to guide explanations and next steps."
