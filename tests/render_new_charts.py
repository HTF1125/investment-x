"""Execute code for newly converted Custom Charts to cache their figures."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ix.db.conn import conn
conn.connect()

from sqlalchemy.orm import Session
from ix.db.models import Charts

with Session(conn.engine) as s:
    # Find charts without cached figures
    charts = s.query(Charts).filter(
        Charts.is_deleted == False,
        Charts.figure == None,
    ).all()
    print(f"Charts without figures: {len(charts)}")

    if not charts:
        print("All charts already have figures cached!")
        sys.exit(0)

    # Import the execution engine
    from ix.common.viz.charting import execute_custom_code

    success = 0
    failed = 0
    errors = []

    for i, chart in enumerate(charts):
        try:
            fig = execute_custom_code(chart.code)
            if fig:
                chart.figure = fig
                success += 1
            else:
                failed += 1
                errors.append((chart.name, "No figure returned"))
        except Exception as e:
            failed += 1
            err_msg = str(e)[:100]
            errors.append((chart.name, err_msg))

        if (i + 1) % 10 == 0:
            s.commit()  # Commit in batches
            print(f"  ... {i + 1}/{len(charts)} processed ({success} ok, {failed} err)")

    s.commit()
    print(f"\nDone!")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")

    if errors:
        print(f"\n  Failed charts:")
        for name, err in errors[:20]:
            print(f"    - {name}: {err}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more")
