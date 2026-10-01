"""Idempotent helpers for Alembic upgrades (greenfield-safe after 0002 create_all)."""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


def table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    return column in cols


def index_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(ix["name"] == name for ix in sa.inspect(bind).get_indexes(table))


def create_table_if_missing(name: str, *args, **kwargs) -> bool:
    """Create a table when absent. Returns True if created."""
    if table_exists(name):
        return False
    op.create_table(name, *args, **kwargs)
    return True


def add_column_if_missing(table: str, column: sa.Column) -> bool:
    if not table_exists(table) or column_exists(table, column.name):
        return False
    op.add_column(table, column)
    return True


def create_index_if_missing(
    name: str,
    table: str,
    columns: Sequence[str],
    **kwargs,
) -> bool:
    if not table_exists(table) or index_exists(table, name):
        return False
    op.create_index(name, table, list(columns), **kwargs)
    return True
