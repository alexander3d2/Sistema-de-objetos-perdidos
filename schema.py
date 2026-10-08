"""Additive, idempotent upgrade of a legacy (priced inventory) SQLite `item` table.

Nothing is dropped, renamed or deleted: legacy columns such as `quantity` and `price`
stay in the table, and only NULL fields are backfilled. SQLite only.
"""

from dataclasses import dataclass, field

from domain import DEFAULT_STATUS, normalize_legacy_category

TABLE = "item"
UNSPECIFIED_LOCATION = "Sin especificar"

# (column, DDL type) in the order they are added.
NEW_COLUMNS = (
    ("location", "VARCHAR(120)"),
    ("event_date", "DATE"),
    ("status", f"VARCHAR(20) NOT NULL DEFAULT '{DEFAULT_STATUS}'"),
    ("contact", "VARCHAR(120)"),
)


@dataclass(frozen=True)
class UpgradeResult:
    table_found: bool = False
    columns_added: tuple = ()
    backfilled: dict = field(default_factory=dict)

    @property
    def changed(self):
        return bool(self.columns_added or self.backfilled)

    def describe(self):
        if not self.table_found:
            return "Legacy schema upgrade: item table not found, nothing changed."
        if not self.changed:
            return "Legacy schema upgrade: nothing changed."
        parts = []
        if self.columns_added:
            parts.append("columns added: " + ", ".join(self.columns_added))
        if self.backfilled:
            parts.append(
                "rows backfilled: "
                + ", ".join(f"{name}={count}" for name, count in self.backfilled.items())
            )
        return "Legacy schema upgrade: " + "; ".join(parts) + "."


def _existing_columns(conn):
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({TABLE})")}


def _backfill_category(conn):
    rows = conn.exec_driver_sql(
        f"SELECT id, category FROM {TABLE} WHERE category IS NOT NULL"
    ).fetchall()
    updated = 0
    for row_id, stored in rows:
        normalized = normalize_legacy_category(stored)
        if normalized is not None and normalized != stored:
            conn.exec_driver_sql(
                f"UPDATE {TABLE} SET category = ? WHERE id = ?", (normalized, row_id)
            )
            updated += 1
    return updated


def upgrade_legacy_schema(engine):
    """Add the lost-and-found columns to a legacy `item` table and backfill NULL fields."""
    with engine.begin() as conn:
        columns = _existing_columns(conn)
        if not columns:
            return UpgradeResult(table_found=False)

        added = []
        for name, ddl in NEW_COLUMNS:
            if name not in columns:
                conn.exec_driver_sql(f"ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}")
                added.append(name)

        backfilled = {}
        statements = (
            (
                "event_date",
                f"UPDATE {TABLE} SET event_date = date(created_at) "
                "WHERE event_date IS NULL AND date(created_at) IS NOT NULL",
            ),
            (
                "location",
                f"UPDATE {TABLE} SET location = '{UNSPECIFIED_LOCATION}' WHERE location IS NULL",
            ),
        )
        for name, sql in statements:
            count = conn.exec_driver_sql(sql).rowcount
            if count > 0:
                backfilled[name] = count
        count = _backfill_category(conn)
        if count > 0:
            backfilled["category"] = count

    return UpgradeResult(table_found=True, columns_added=tuple(added), backfilled=backfilled)
