from ix.db.conn import Session
from ix.db.models.chart import Chart
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def refresh_all():
    """Fetches all charts and forces a re-render to update cached figures."""
    with Session() as s:
        charts = s.query(Chart).all()
        logger.info(f"Found {len(charts)} charts to refresh.")

        for chart in charts:
            try:
                logger.info(f"Refreshing {chart.code} ({chart.category})...")
                # Force update simply by calling update_figure which calls render(force_update=True)
                chart.update_figure()
            except Exception as e:
                logger.error(f"Failed to refresh {chart.code}: {e}")

        s.commit()
        logger.info("All charts processed.")


if __name__ == "__main__":
    refresh_all()
