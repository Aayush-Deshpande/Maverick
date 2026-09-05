"""
Report content -> renderable lines — DRDO / iDEX PS-26054

The viewer never re-derives report data; it only formats whatever the simulation
already wrote. This module turns a loaded JSON / CSV / Markdown report into a flat
list of typed lines the GPU text panel can draw and scroll.

Line format: (kind, primary, secondary, indent)
    kind      'h1' | 'h2' | 'kv' | 'text' | 'bullet' | 'rule' | 'blank'
    primary   heading text, key name, or body text
    secondary value text (kv only), else ""
    indent    nesting depth, rendered as a left offset

Stdlib only.
"""

import os
from typing import Any, Dict, List, Tuple

Line = Tuple[str, str, str, int]

_MAX_LIST_ITEMS = 200   # a report listing more rows than this is elided with a count
_MAX_CSV_ROWS = 120


def format_report(loaded: Dict[str, Any], title: str, path: str) -> List[Line]:
    """Build the full renderable document for one opened report."""
    lines: List[Line] = [
        ("h1", title, "", 0),
        ("text", os.path.basename(path), "", 0),
        ("rule", "", "", 0),
    ]

    kind = loaded.get("kind")
    if kind == "json":
        lines.extend(_format_value(loaded.get("data"), 0))
    elif kind == "csv":
        lines.extend(_format_csv(loaded.get("rows") or []))
    elif kind == "error":
        lines.append(("text", loaded.get("text", "Unknown error"), "", 0))
    else:
        lines.extend(_format_markdown(loaded.get("text", "")))

    if loaded.get("truncated"):
        lines.append(("blank", "", "", 0))
        lines.append(("text", "— report truncated for display; full file on disk —", "", 0))
    return lines


# ----------------------------------------------------------------------
# JSON
# ----------------------------------------------------------------------

def _format_value(value: Any, indent: int) -> List[Line]:
    if isinstance(value, dict):
        return _format_dict(value, indent)
    if isinstance(value, list):
        return _format_list(value, indent)
    return [("text", _scalar(value), "", indent)]


def _format_dict(data: Dict[str, Any], indent: int) -> List[Line]:
    """Scalars first as an aligned key/value block, then nested structures as sections."""
    lines: List[Line] = []
    nested: List[Tuple[str, Any]] = []

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            nested.append((key, value))
        else:
            lines.append(("kv", _humanise(key), _scalar(value), indent))

    for key, value in nested:
        lines.append(("blank", "", "", 0))
        lines.append(("h2", _humanise(key), "", indent))
        if isinstance(value, dict):
            lines.extend(_format_dict(value, indent + 1))
        else:
            lines.extend(_format_list(value, indent + 1))
    return lines


def _format_list(items: List[Any], indent: int) -> List[Line]:
    lines: List[Line] = []
    if not items:
        lines.append(("text", "(none)", "", indent))
        return lines

    shown = items[:_MAX_LIST_ITEMS]
    for i, item in enumerate(shown):
        if isinstance(item, dict):
            if i:
                lines.append(("blank", "", "", 0))
            header, body = _split_record(item)
            lines.append(("bullet", header, "", indent))
            for key, value in body:
                if isinstance(value, (dict, list)):
                    lines.append(("h2", _humanise(key), "", indent + 1))
                    lines.extend(_format_value(value, indent + 2))
                else:
                    lines.append(("kv", _humanise(key), _scalar(value), indent + 1))
        elif isinstance(item, list):
            lines.extend(_format_list(item, indent + 1))
        else:
            lines.append(("bullet", _scalar(item), "", indent))

    if len(items) > len(shown):
        lines.append(("blank", "", "", 0))
        lines.append(("text", f"… {len(items) - len(shown)} more entries in the report file", "", indent))
    return lines


def _split_record(item: Dict[str, Any]) -> Tuple[str, List[Tuple[str, Any]]]:
    """
    Promote the most identifying field of a record to its bullet heading so a long
    list of detections/orders/events scans vertically instead of reading as a wall
    of key/value pairs.
    """
    for key in ("title", "fault_name", "component", "channel", "subsystem",
                "name", "action_id", "event_id", "at"):
        if key in item and not isinstance(item[key], (dict, list)):
            head = _scalar(item[key])
            prefix = ""
            if key == "title" and "at" in item:
                prefix = f"{_scalar(item['at'])}   "
            rest = [(k, v) for k, v in item.items() if k != key and not (k == "at" and prefix)]
            return prefix + head, rest
    return "entry", list(item.items())


# ----------------------------------------------------------------------
# CSV
# ----------------------------------------------------------------------

def _format_csv(rows: List[List[str]]) -> List[Line]:
    if not rows:
        return [("text", "(empty log)", "", 0)]

    header, *body = rows
    lines: List[Line] = [
        ("h2", "Channels", "", 0),
        ("text", ", ".join(header), "", 0),
        ("blank", "", "", 0),
        ("h2", f"Samples ({len(body)} shown)", "", 0),
    ]
    for row in body[:_MAX_CSV_ROWS]:
        lines.append(("text", "  ".join(f"{c:>10}" for c in row), "", 0))
    if len(body) > _MAX_CSV_ROWS:
        lines.append(("blank", "", "", 0))
        lines.append(("text", f"… {len(body) - _MAX_CSV_ROWS} further rows in the log file", "", 0))
    return lines


# ----------------------------------------------------------------------
# Markdown
# ----------------------------------------------------------------------

def _format_markdown(text: str) -> List[Line]:
    lines: List[Line] = []
    in_frontmatter = False

    for raw in text.splitlines():
        stripped = raw.strip()

        if stripped == "---":
            # YAML frontmatter fences open/close a metadata block; the fence itself
            # renders as a rule rather than as literal dashes.
            in_frontmatter = not in_frontmatter
            lines.append(("rule", "", "", 0))
            continue

        if not stripped:
            lines.append(("blank", "", "", 0))
            continue

        if in_frontmatter:
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                lines.append(("kv", _humanise(key.strip()), _clean(value.strip()), 0))
            else:
                lines.append(("text", _clean(stripped), "", 0))
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            lines.append(("h1" if level <= 1 else "h2", _clean(stripped.lstrip("#").strip()), "", 0))
            continue

        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # markdown table separator row
            lines.append(("text", "   ".join(_clean(c) for c in cells), "", 0))
            continue

        if stripped.startswith(("- ", "* ", "+ ")):
            body = stripped[2:].strip()
            indent = (len(raw) - len(raw.lstrip())) // 2
            if body.startswith("[x]") or body.startswith("[ ]"):
                mark = "[DONE]" if body.startswith("[x]") else "[OPEN]"
                lines.append(("bullet", f"{mark}  {_clean(body[3:].strip())}", "", indent))
            else:
                lines.append(("bullet", _clean(body), "", indent))
            continue

        lines.append(("text", _clean(stripped), "", 0))

    return lines


def _clean(text: str) -> str:
    """Strip the markdown emphasis/code markers that would otherwise render literally."""
    return text.replace("**", "").replace("`", "").replace("*", "")


# ----------------------------------------------------------------------
# Shared
# ----------------------------------------------------------------------

def _humanise(key: str) -> str:
    return str(key).replace("_", " ").strip().title()


def _scalar(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if abs(value) < 1e6 else f"{value:.1f}"
    return str(value)
