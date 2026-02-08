"""Test chart update persistence."""

from ix.db.conn import Session
from ix.db.models import Chart
from datetime import datetime

print(f"Test started at {datetime.now()}")

# Get current state
with Session() as s:
    chart = s.query(Chart).filter(Chart.code == "AsianExportsYoY").first()
    print(f"Before update: updated_at = {chart.updated_at}")
    old_time = chart.updated_at

# Update in new session - let context manager commit
with Session() as s:
    chart = s.query(Chart).filter(Chart.code == "AsianExportsYoY").first()
    print(f"Calling update_figure...")
    chart.update_figure()
    print(f"After update_figure: updated_at = {chart.updated_at}")
    # Don't call s.commit() - context manager will do it

# Verify in another new session
with Session() as s:
    chart = s.query(Chart).filter(Chart.code == "AsianExportsYoY").first()
    print(f"Verification in new session: updated_at = {chart.updated_at}")
    if chart.updated_at != old_time:
        print("SUCCESS: Timestamp was updated!")
    else:
        print("FAILURE: Timestamp was NOT updated!")

print("Test complete")
