# Why is this taking so long?
#
# Main bottleneck here is likely repeated session.flush(),
# large data being deserialized/evaluated or written for each row,
# or expensive database I/O inside the loop.
# Let's instrument timing and reduce flush frequency for diagnostics.

import time
import logging
from ix.db import Timeseries
from ix.db.conn import Session
from ix.engine import execute_source_code

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with Session() as session:
    timeseries_rows = (
        session.query(Timeseries.id, Timeseries.code, Timeseries.source_code)
        .filter(Timeseries.source == "InvestmentX")
        .all()
    )

    logger.info(f"Fetched {len(timeseries_rows)} timeseries rows.")

    n = 0
    start_time = time.time()
    for row_id, row_code, row_source_code in timeseries_rows:
        logger.info(f"Processing row_code: {row_code}")
        n += 1
        t0 = time.time()
        # Try to measure eval/processing
        try:
            s_eval = time.time()
            data = execute_source_code(str(row_source_code))
            s_eval_done = time.time()
            if hasattr(data, "dropna"):
                data = data.dropna()
            data.name = row_code
        except Exception as e:
            logger.error(f"Error evaluating row {row_id} ({row_code}): {e}")
            continue
        s_proc_done = time.time()

        # Print timing
        logger.info(
            f"[{n}/{len(timeseries_rows)}] eval: {s_eval_done-s_eval:.3f}s, proc: {s_proc_done-s_eval_done:.3f}s"
        )

        # ORM update and session flush timing
        t_db0 = time.time()
        ts_row = session.get(Timeseries, row_id)
        ts_row.reset()
        ts_row.data = data.to_dict()
        t_db1 = time.time()
        logger.info(
            f"    DB update: {t_db1-t_db0:.3f}s, total {t_db1-t0:.3f}s for this row, elapsed: {t_db1-start_time:.1f}s"
        )

        # If this is slow, try commenting out flush() in-loop and only flush/commit at end.
    session.commit()
    logger.info("Done. Total time: %.2fs" % (time.time() - start_time))
