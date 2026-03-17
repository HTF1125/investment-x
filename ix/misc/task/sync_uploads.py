"""
Polls R2 for pending upload files and merges them into local + cloud DB.
Runs as a scheduled job on local env only.
"""
import pandas as pd
from ix.misc import get_logger

logger = get_logger(__name__)


def sync_uploads_from_r2():
    """Process all pending R2 upload files into local + cloud DB."""
    from ix.db.boto import Boto
    from ix.db.conn import ensure_connection, Session, cloud_session
    from ix.db.models import Timeseries
    from datetime import datetime

    try:
        storage = Boto()
        pending = [
            k for k in storage.list_prefix("uploads/")
            if not k.startswith("uploads/processed/")
        ]
    except Exception as e:
        logger.error("R2 sync: failed to list uploads: %s", e)
        return

    if not pending:
        return  # Nothing to do — silent

    logger.info("R2 sync: found %d pending file(s)", len(pending))
    ensure_connection()

    for key in sorted(pending):
        try:
            data = storage.get_json(key)
            if not data:
                logger.warning("R2 sync: empty/invalid JSON: %s", key)
                continue

            # Parse into DataFrame
            fmt = data.get("format", "")
            if fmt == "columnar":
                dates_index = pd.to_datetime(data["dates"], errors="coerce")
                df = pd.DataFrame(data["columns"], index=dates_index)
            elif fmt == "row":
                records = data.get("records", [])
                raw = pd.DataFrame(records)
                raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
                raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
                raw = raw.dropna(subset=["value", "date", "code"])
                if raw.empty:
                    continue
                df = raw.pivot(index="date", columns="code", values="value").sort_index()
                df.index = pd.to_datetime(df.index)
            else:
                logger.warning("R2 sync: unknown format in %s: %s", key, fmt)
                continue

            df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
            if df.empty:
                storage.rename_file(key, key.replace("uploads/", "uploads/processed/", 1))
                continue

            # Merge into local DB
            with Session() as db:
                result = _merge_to_db(df, db, Timeseries)
                logger.info(
                    "R2 sync [local]: %s -> %d codes, %d points",
                    key, len(result["updated"]), result["points"],
                )

            # Merge into cloud DB
            try:
                with cloud_session() as cloud_db:
                    if cloud_db is not None:
                        cloud_result = _merge_to_db(df, cloud_db, Timeseries)
                        logger.info(
                            "R2 sync [cloud]: %s -> %d codes, %d points",
                            key, len(cloud_result["updated"]), cloud_result["points"],
                        )
            except Exception as e:
                logger.exception("R2 sync: cloud DB failed for %s: %s", key, e)

            # Move to processed
            storage.rename_file(key, key.replace("uploads/", "uploads/processed/", 1))

        except Exception as e:
            logger.exception("R2 sync: failed to process %s: %s", key, e)


def _merge_to_db(df: pd.DataFrame, db, Timeseries) -> dict:
    """Merge a date-indexed DataFrame into the given DB session."""
    from datetime import datetime

    updated = []
    not_found = []
    total_points = 0

    for code in df.columns:
        ts = db.query(Timeseries).filter(Timeseries.code == code).first()
        if ts is None:
            not_found.append(code)
            continue

        data_record = ts._get_or_create_data_record(db)
        column_data = data_record.data if data_record and data_record.data else {}

        if column_data and isinstance(column_data, dict):
            existing = pd.Series(column_data)
            if not existing.empty:
                existing.index = pd.to_datetime(existing.index, errors="coerce")
                existing = existing.dropna()
        else:
            existing = pd.Series(dtype=float)

        new_series = df[code].dropna()

        if not existing.empty:
            combined = pd.concat([existing, new_series], axis=0)
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        else:
            combined = new_series.sort_index()

        data_dict = {}
        for k, v in combined.to_dict().items():
            date_str = str(k.date()) if hasattr(k, "date") else str(pd.to_datetime(k).date()) if not isinstance(k, str) else k
            data_dict[date_str] = float(v) if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

        data_record.data = data_dict
        data_record.updated = datetime.now()
        ts.start = combined.index.min().date() if len(combined) > 0 else None
        ts.end = combined.index.max().date() if len(combined) > 0 else None
        ts.num_data = len(combined)
        ts.updated = datetime.now()

        total_points += len(new_series)
        updated.append(code)

    db.commit()
    return {"updated": updated, "not_found": not_found, "points": total_points}
