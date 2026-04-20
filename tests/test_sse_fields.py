"""Regression test: verify frontend SSE field names match backend emitted field names."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _extract_frontend_fields(js_path: Path) -> set[str]:
    """Extract event field names used in handleEvent() from app.js."""
    text = js_path.read_text()
    # Match event.<field> patterns inside handleEvent
    fn_match = re.search(r"function handleEvent\(event\)\s*\{(.*?)\n  \}", text, re.DOTALL)
    assert fn_match, "handleEvent() not found in app.js"
    body = fn_match.group(1)
    # event.<field> where field is a word (excludes method calls)
    fields = set(re.findall(r"event\.(\w+)", body))
    return fields


def _extract_backend_fields(py_path: Path) -> set[str]:
    """Extract event dict keys emitted by the orchestrator."""
    text = py_path.read_text()
    # Find all dict literals passed to _emit: {"key": ..., "key": ...}
    dicts = re.findall(r'_emit\(\{([^}]+)\}\)', text)
    keys: set[str] = set()
    for d in dicts:
        keys.update(re.findall(r'"(\w+)"', d))
    return keys


def test_frontend_uses_backend_event_field():
    """The frontend must use 'event' (not 'type') to read the event kind."""
    js_path = REPO_ROOT / "static" / "app.js"
    fields = _extract_frontend_fields(js_path)
    assert "event" in fields, f"Frontend should access event.event, found fields: {fields}"
    assert "type" not in fields, f"Frontend should NOT use event.type, found fields: {fields}"


def test_frontend_uses_backend_data_field():
    """The frontend must use 'data' (not 'content') to read the result payload."""
    js_path = REPO_ROOT / "static" / "app.js"
    fields = _extract_frontend_fields(js_path)
    assert "data" in fields, f"Frontend should access event.data, found fields: {fields}"
    assert "content" not in fields, f"Frontend should NOT use event.content, found fields: {fields}"


def test_frontend_fields_subset_of_backend():
    """All field names used in frontend handleEvent() must exist in backend _emit() calls."""
    js_path = REPO_ROOT / "static" / "app.js"
    py_path = REPO_ROOT / "src" / "agents" / "orchestrator.py"
    fe_fields = _extract_frontend_fields(js_path)
    be_fields = _extract_backend_fields(py_path)
    # Frontend accesses event.message too, which is a backend field
    missing = fe_fields - be_fields
    assert not missing, f"Frontend uses fields not emitted by backend: {missing}"
