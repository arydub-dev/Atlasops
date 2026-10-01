"""HTML escaping for outbound email bodies."""
from __future__ import annotations

import html


def escape_html(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)
