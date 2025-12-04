# Why is this taking so long?
#
# Main bottleneck here is likely repeated session.flush(),
# large data being deserialized/evaluated or written for each row,
# or expensive database I/O inside the loop.
# Let's instrument timing and reduce flush frequency for diagnostics.

import time
from ix.db import Timeseries
from ix.db.conn import Session
from ix.db.query import (
    Offset,
    Series,
    MultiSeries,
    M2,
    MonthEndOffset,
    NumOfOECDLeadingPositiveMoM,
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
    financial_conditions_us,
    FedNetLiquidity,
)
from ix.db.query import *
with Session() as session:
    timeseries_rows = (
        session.query(Timeseries.id, Timeseries.code, Timeseries.source_code)
        .filter(Timeseries.source == "InvestmentX")
        .all()
    )

    print(f"Fetched {len(timeseries_rows)} timeseries rows.")

    n = 0
    start_time = time.time()
    for row_id, row_code, row_source_code in timeseries_rows:
        print(row_code)
        n += 1
        t0 = time.time()
        # Try to measure eval/processing
        try:
            s_eval = time.time()
            data = eval(
                str(row_source_code)
            )  # Beware: eval is potentially slow/dangerous!
            s_eval_done = time.time()
            if hasattr(data, "dropna"):
                data = data.dropna()
            data.name = row_code
        except Exception as e:
            print(f"Error evaluating row {row_id} ({row_code}): {e}")
            continue
        s_proc_done = time.time()

        # Print timing
        print(
            f"[{n}/{len(timeseries_rows)}] eval: {s_eval_done-s_eval:.3f}s, proc: {s_proc_done-s_eval_done:.3f}s"
        )

        # ORM update and session flush timing
        t_db0 = time.time()
        ts_row = session.get(Timeseries, row_id)
        ts_row.reset()
        ts_row.data = data.to_dict()
        session.flush()  # This flush writes pending changes. Could be slow if repeated.
        t_db1 = time.time()
        print(
            f"    DB update + flush: {t_db1-t_db0:.3f}s, total {t_db1-t0:.3f}s for this row, elapsed: {t_db1-start_time:.1f}s"
        )

        # If this is slow, try commenting out flush() in-loop and only flush/commit at end.

    print("Done. Total time: %.2fs" % (time.time() - start_time))
