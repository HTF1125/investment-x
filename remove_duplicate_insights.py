"""
Standalone script to remove duplicate insights.

Usage:
    python remove_duplicate_insights.py          # Dry run (shows what would be deleted)
    python remove_duplicate_insights.py --execute # Actually delete duplicates
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ix.db.migrations.remove_duplicate_insights import main

if __name__ == "__main__":
    sys.exit(main())
