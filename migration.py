"""
Utility helpers for one-off database migrations.

Run as a module:

    python migration.py migrate_timeseries_payloads --batch-size 200
"""

import argparse
from typing import Callable, Dict

from sqlalchemy import text

from ix.db.conn import ensure_connection, Session, conn
from ix.db.models import Timeseries
from ix.misc import get_logger

logger = get_logger(__name__)


def _pretty_size(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    value = float(num)
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} {units[-1]}"


def migrate_timeseries_payloads(batch_size: int = 200) -> int:
    """
    Ensure every Timeseries row has a dedicated TimeseriesData record.

    Legacy JSON stored in the `timeseries.timeseries_data` column is migrated
    into the new `timeseries_data` table via `Timeseries._get_or_create_data_record`.

    Args:
        batch_size: Number of rows to process before committing.

    Returns:
        Total number of timeseries processed.
    """
    ensure_connection()
    processed = 0
    last_id = None

    with Session() as session:
        while True:
            batch_query = session.query(Timeseries).order_by(Timeseries.id)
            if last_id is not None:
                batch_query = batch_query.filter(Timeseries.id > last_id)

            batch = batch_query.limit(batch_size).all()
            if not batch:
                break

            for ts in batch:
                ts._get_or_create_data_record(session)
                processed += 1

            session.commit()
            last_id = batch[-1].id
            session.expunge_all()

            logger.info("Migrated %s timeseries payloads so far", processed)

    logger.info("Completed migration for %s timeseries rows", processed)
    return processed


def drop_legacy_timeseries_column() -> int:
    """
    Drop the legacy JSON column from the timeseries table, if it still exists.
    """
    ensure_connection()

    with conn.engine.begin() as bind:
        bind.execute(
            text("ALTER TABLE IF EXISTS timeseries DROP COLUMN IF EXISTS timeseries_data")
        )

    logger.info("Dropped legacy column timeseries.timeseries_data (if it existed)")
    return 0


def _relation_size_stats(bind, relname: str) -> Dict[str, str]:
    relation_info = bind.execute(
        text(
            """
            SELECT c.oid, n.nspname AS schema_name
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = :rel
            ORDER BY (n.nspname = current_schema()) DESC
            LIMIT 1
            """
        ),
        {"rel": relname},
    ).mappings().one_or_none()

    if relation_info is None:
        raise ValueError(f"Relation {relname!r} does not exist")

    oid = relation_info["oid"]
    schema_name = relation_info["schema_name"]

    size_row = bind.execute(
        text(
            """
            SELECT
                pg_relation_size(:oid) AS table_bytes,
                pg_indexes_size(:oid) AS index_bytes,
                pg_total_relation_size(:oid) AS total_bytes
            """
        ),
        {"oid": oid},
    ).mappings().one()

    toast_bytes = max(
        size_row["total_bytes"] - size_row["table_bytes"] - size_row["index_bytes"], 0
    )

    stat_row = bind.execute(
        text(
            """
            SELECT
                COALESCE(n_live_tup, 0) AS n_live_tup,
                COALESCE(n_dead_tup, 0) AS n_dead_tup,
                COALESCE(vacuum_count, 0) AS vacuum_count,
                COALESCE(autovacuum_count, 0) AS autovacuum_count,
                COALESCE(analyze_count, 0) AS analyze_count,
                COALESCE(autoanalyze_count, 0) AS autoanalyze_count,
                COALESCE(last_vacuum::text, 'never') AS last_vacuum,
                COALESCE(last_autovacuum::text, 'never') AS last_autovacuum,
                COALESCE(last_analyze::text, 'never') AS last_analyze,
                COALESCE(last_autoanalyze::text, 'never') AS last_autoanalyze
            FROM pg_stat_user_tables
            WHERE relname = :rel AND schemaname = :schema
            """
        ),
        {"rel": relname, "schema": schema_name},
    ).mappings().one_or_none()

    preparer = bind.dialect.identifier_preparer
    qualified_name = (
        f"{preparer.quote_identifier(schema_name)}."
        f"{preparer.quote_identifier(relname)}"
    )

    rowcount = bind.execute(text(f"SELECT COUNT(*) FROM {qualified_name}")).scalar_one()

    return {
        "table_pretty": _pretty_size(size_row["table_bytes"]),
        "index_pretty": _pretty_size(size_row["index_bytes"]),
        "toast_pretty": _pretty_size(toast_bytes),
        "total_pretty": _pretty_size(size_row["total_bytes"]),
        "table_bytes": size_row["table_bytes"],
        "index_bytes": size_row["index_bytes"],
        "toast_bytes": toast_bytes,
        "total_bytes": size_row["total_bytes"],
        "n_live_tup": (stat_row or {}).get("n_live_tup", 0),
        "n_dead_tup": (stat_row or {}).get("n_dead_tup", 0),
        "vacuum_count": (stat_row or {}).get("vacuum_count", 0),
        "autovacuum_count": (stat_row or {}).get("autovacuum_count", 0),
        "analyze_count": (stat_row or {}).get("analyze_count", 0),
        "autoanalyze_count": (stat_row or {}).get("autoanalyze_count", 0),
        "last_vacuum": (stat_row or {}).get("last_vacuum", "never"),
        "last_autovacuum": (stat_row or {}).get("last_autovacuum", "never"),
        "last_analyze": (stat_row or {}).get("last_analyze", "never"),
        "last_autoanalyze": (stat_row or {}).get("last_autoanalyze", "never"),
        "rowcount": rowcount or 0,
    }


def show_timeseries_size() -> int:
    """
    Report size statistics for timeseries-related tables.
    """
    ensure_connection()

    with conn.engine.connect() as bind:
        ts_stats = _relation_size_stats(bind, "timeseries")
        data_stats = _relation_size_stats(bind, "timeseries_data")

    logger.info("Timeseries table size: %s (table=%s, indexes=%s, toast=%s)", ts_stats["total_pretty"], ts_stats["table_pretty"], ts_stats["index_pretty"], ts_stats["toast_pretty"])
    logger.info(
        "Timeseries rows: %s live / %s dead; vacuumed %s times (auto %s); last autovacuum=%s",
        ts_stats["n_live_tup"],
        ts_stats["n_dead_tup"],
        ts_stats["vacuum_count"],
        ts_stats["autovacuum_count"],
        ts_stats["last_autovacuum"],
    )
    logger.info(
        "Timeseries data table size: %s (table=%s, indexes=%s, toast=%s)",
        data_stats["total_pretty"],
        data_stats["table_pretty"],
        data_stats["index_pretty"],
        data_stats["toast_pretty"],
    )
    logger.info(
        "Timeseries data rows: %s live / %s dead; vacuumed %s times (auto %s); last autovacuum=%s",
        data_stats["n_live_tup"],
        data_stats["n_dead_tup"],
        data_stats["vacuum_count"],
        data_stats["autovacuum_count"],
        data_stats["last_autovacuum"],
    )
    return 0


def vacuum_full_timeseries(include_data: bool = True) -> int:
    """
    Run VACUUM FULL against the timeseries tables to reclaim space.

    Args:
        include_data: also VACUUM FULL the timeseries_data table.
    """
    ensure_connection()

    tables = ["timeseries"]
    if include_data:
        tables.append("timeseries_data")

    with conn.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as bind:
        for table in tables:
            logger.info("Running VACUUM FULL on %s...", table)
            bind.execute(text(f"VACUUM FULL {table}"))
            logger.info("Completed VACUUM FULL on %s", table)

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Database migration utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    payloads_parser = subparsers.add_parser(
        "migrate_timeseries_payloads",
        help="Populate the new timeseries_data table from legacy JSON column.",
    )
    payloads_parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Rows to process per transaction commit (default: 200).",
    )

    subparsers.add_parser(
        "drop_legacy_timeseries_column",
        help="Drop the old timeseries.timeseries_data JSON column.",
    )

    subparsers.add_parser(
        "show_timeseries_size",
        help="Print size statistics for timeseries and timeseries_data tables.",
    )

    vacuum_parser = subparsers.add_parser(
        "vacuum_full_timeseries",
        help="Run VACUUM FULL on the timeseries tables to reclaim space.",
    )
    vacuum_parser.add_argument(
        "--skip-data",
        dest="include_data",
        action="store_false",
        help="Skip vacuuming the timeseries_data table.",
    )

    return parser.parse_args()


def _dispatch(args: argparse.Namespace) -> int:
    commands: Dict[str, Callable[..., int]] = {
        "migrate_timeseries_payloads": migrate_timeseries_payloads,
        "drop_legacy_timeseries_column": drop_legacy_timeseries_column,
        "show_timeseries_size": show_timeseries_size,
        "vacuum_full_timeseries": vacuum_full_timeseries,
    }

    command = commands.get(args.command)
    if command is None:
        raise ValueError(f"Unknown command: {args.command}")

    kwargs = {k: v for k, v in vars(args).items() if k not in {"command"}}
    return command(**kwargs)


def main() -> None:
    args = _parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()
