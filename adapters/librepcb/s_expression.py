# Global imports
import uuid
from datetime import datetime
from typing import Any, List, Tuple, Union

# Sentinel for explicit line breaks
LINEBREAK = object()


class SExpSymbol:
    def __init__(self, val: str):
        self.value = val


def _format_token(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int,)):
        return str(val)
    if isinstance(val, float):
        s = f"{val:.3f}"
        s = s.rstrip("0").rstrip(".")
        return s + (".0" if "." not in s else "")
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, SExpSymbol):
        return val.value
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%dT%H:%M:%SZ")
    if val is None:
        return ""
    # fallback to quoted string
    s = str(val).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _serialize_node(node: Union[Tuple[str, List[Any]]], indent: int = 0) -> str:
    """Recursively serialize a (tag, contents) tuple."""
    tag, contents = node
    pad = " " * indent
    s = f"{pad}({tag}"
    first = True
    for item in contents:
        if item is LINEBREAK:
            s += "\n" + pad + " "  # newline + one-space indent
            first = True
        elif isinstance(item, tuple):
            # nested list
            s += "\n" + _serialize_node(item, indent + 1)
            first = False
        else:
            tok = _format_token(item)
            if first:
                s += " " + tok
            else:
                s += "\n" + pad + " " + tok
            first = False
    s += ")"
    return s


def serialize_to_sexpr(root_tag: str, contents: List[Any]) -> str:
    """Wrapper: builds and returns the full S-expression with trailing newline."""
    text = _serialize_node((root_tag, contents), indent=0)
    return text + "\n"
