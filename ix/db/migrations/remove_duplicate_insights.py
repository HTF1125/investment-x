"""
Migration script to remove duplicate insights.

Duplicate criteria:
- Same published_date
- Same name
- Same issuer

Deletion rules:
1. If one has a summary and one doesn't, delete the one without summary
2. If both have summaries (or both don't), delete the one with the later ID (keep older)
3. If both have no summaries, delete the one with the later ID (keep older)
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from ix.db.conn import Session, ensure_connection
from ix.db.models import Insights
from ix.misc.terminal import get_logger
from datetime import date

logger = get_logger(__name__)


def find_duplicate_groups() -> Dict[Tuple[str, str, date], List[Dict]]:
    """
    Find groups of duplicate insights based on (name, issuer, published_date).

    Returns:
        Dictionary mapping (name, issuer, published_date) tuple to list of insight dicts
    """
    logger.info("Finding duplicate insights...")

    with Session() as session:
        # Get all insights ordered by published_date and id
        all_insights = (
            session.query(Insights)
            .order_by(Insights.published_date, Insights.id)
            .all()
        )

        # Extract data while in session
        insight_data_list = []
        for insight in all_insights:
            # Normalize name and issuer for comparison (case-insensitive)
            name = (insight.name or "").strip().lower()
            issuer = (insight.issuer or "").strip().lower()
            pub_date = insight.published_date
            has_summary = bool(insight.summary and str(insight.summary).strip())

            # Store as dict to avoid detached instance errors
            insight_data_list.append({
                "id": str(insight.id),
                "name": insight.name or "",
                "issuer": insight.issuer or "",
                "published_date": pub_date,
                "has_summary": has_summary,
                "summary": insight.summary or "",
                "normalized_name": name,
                "normalized_issuer": issuer,
            })

        # Group by (normalized_name, normalized_issuer, published_date)
        groups = defaultdict(list)
        for insight_data in insight_data_list:
            key = (
                insight_data["normalized_name"],
                insight_data["normalized_issuer"],
                insight_data["published_date"]
            )
            groups[key].append(insight_data)

        # Filter to only groups with duplicates (more than 1)
        duplicate_groups = {
            key: insights for key, insights in groups.items()
            if len(insights) > 1
        }

        logger.info(f"Found {len(duplicate_groups)} groups with duplicates")
        total_duplicates = sum(len(insights) - 1 for insights in duplicate_groups.values())
        logger.info(f"Total duplicate insights to process: {total_duplicates}")

        return duplicate_groups


def select_insights_to_delete(duplicate_insights: List[Dict]) -> List[Dict]:
    """
    Determine which insights from a duplicate group should be deleted.

    Args:
        duplicate_insights: List of insight dicts that are duplicates

    Returns:
        List of insight dicts to delete
    """
    if len(duplicate_insights) <= 1:
        return []

    # Sort by: has summary (True first), then by id (older first)
    # This way we keep the one with summary, or the oldest if both have/ don't have summary
    def sort_key(insight: Dict) -> Tuple[bool, str]:
        has_summary = insight.get("has_summary", False)
        # Invert has_summary so True comes first (False < True, but we want True first)
        return (not has_summary, insight.get("id", ""))

    sorted_insights = sorted(duplicate_insights, key=sort_key)

    # Keep the first one (has summary and oldest, or oldest if no summary)
    # Delete all others
    insights_to_delete = sorted_insights[1:]

    return insights_to_delete


def remove_duplicates(dry_run: bool = True) -> Tuple[int, List[Dict]]:
    """
    Remove duplicate insights based on the rules.

    Args:
        dry_run: If True, only log what would be deleted without actually deleting

    Returns:
        Tuple of (number_of_deleted_insights, list_of_deleted_info)
    """
    if not ensure_connection():
        logger.error("Failed to connect to database")
        return 0, []

    # Find duplicate groups
    duplicate_groups = find_duplicate_groups()

    if not duplicate_groups:
        logger.info("No duplicate insights found!")
        return 0, []

    # Collect insights to delete
    all_to_delete = []
    deleted_info = []

    for (name, issuer, pub_date), insights in duplicate_groups.items():
        to_delete = select_insights_to_delete(insights)
        kept = [insight for insight in insights if insight not in to_delete][0]

        for insight_data in to_delete:
            all_to_delete.append(insight_data)
            deleted_info.append({
                "id": insight_data.get("id"),
                "name": insight_data.get("name"),
                "issuer": insight_data.get("issuer"),
                "published_date": str(insight_data.get("published_date")) if insight_data.get("published_date") else None,
                "has_summary": insight_data.get("has_summary", False),
                "kept_id": kept.get("id"),
                "kept_has_summary": kept.get("has_summary", False),
            })

    logger.info(f"\n{'DRY RUN - ' if dry_run else ''}Found {len(all_to_delete)} insights to delete")

    if dry_run:
        logger.info("\n=== DRY RUN - No deletions performed ===")
        logger.info("Duplicates to be deleted:")
        for info in deleted_info[:10]:  # Show first 10
            logger.info(
                f"  - ID: {info['id']}, Name: {info['name']}, "
                f"Summary: {'Yes' if info['has_summary'] else 'No'} "
                f"(Kept ID: {info['kept_id']}, Summary: {'Yes' if info['kept_has_summary'] else 'No'})"
            )
        if len(deleted_info) > 10:
            logger.info(f"  ... and {len(deleted_info) - 10} more")
        return 0, deleted_info

    # Actually delete
    deleted_count = 0
    with Session() as session:
        for insight_data in all_to_delete:
            try:
                insight_id = insight_data.get("id")
                # Re-fetch the insight in this session to ensure it's attached
                insight_to_delete = session.query(Insights).filter(Insights.id == insight_id).first()
                if insight_to_delete:
                    logger.debug(f"Deleting insight ID: {insight_to_delete.id}, Name: {insight_to_delete.name}")
                    session.delete(insight_to_delete)
                    deleted_count += 1
                else:
                    logger.warning(f"Insight {insight_id} not found in database (may have been already deleted)")
            except Exception as e:
                logger.error(f"Error deleting insight {insight_data.get('id')}: {e}")
                continue

        try:
            session.commit()
            logger.info(f"\n✅ Successfully deleted {deleted_count} duplicate insights")
        except Exception as e:
            session.rollback()
            logger.error(f"Error committing deletions: {e}")
            raise

    return deleted_count, deleted_info


def main():
    """Main entry point for the script."""
    import sys

    # Check if dry-run flag is passed
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("=" * 60)
        print("DUPLICATE INSIGHTS REMOVAL - DRY RUN MODE")
        print("=" * 60)
        print("This is a dry run. No deletions will be performed.")
        print("Use --execute flag to actually delete duplicates.")
        print("=" * 60)
    else:
        print("=" * 60)
        print("DUPLICATE INSIGHTS REMOVAL - EXECUTION MODE")
        print("=" * 60)
        print("⚠️  WARNING: This will permanently delete duplicate insights!")
        print("=" * 60)

    try:
        deleted_count, deleted_info = remove_duplicates(dry_run=dry_run)

        if dry_run:
            print(f"\n{'=' * 60}")
            print(f"DRY RUN COMPLETE")
            print(f"Would delete {len(deleted_info)} duplicate insights")
            print(f"{'=' * 60}")
            print("\nTo execute the deletion, run:")
            print("  python -m ix.db.migrations.remove_duplicate_insights --execute")
        else:
            print(f"\n{'=' * 60}")
            print(f"✅ DELETION COMPLETE")
            print(f"Deleted {deleted_count} duplicate insights")
            print(f"{'=' * 60}")

        return 0

    except Exception as e:
        logger.exception(f"Error removing duplicates: {e}")
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
