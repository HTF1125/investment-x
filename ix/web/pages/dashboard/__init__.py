"""
Dashboard module for Investment X web application.

This module provides a modular dashboard structure with the following components:
- data_manager: Handles data loading, caching, and background refresh
- visualizations: Manages heatmap generation and chart utilities
- ui_components: Provides skeleton loaders, error displays, and layout helpers
- callbacks: Manages all dashboard callbacks and event handlers
- layout: Main dashboard layout and page registration
"""

from ix.web.pages.dashboard.data_manager import DataManager, BackgroundRefreshManager
from ix.web.pages.dashboard.visualizations import HeatmapGenerator, ChartUtilities
from ix.web.pages.dashboard.ui_components import SkeletonLoader, ErrorDisplay, LayoutHelpers
from ix.web.pages.dashboard.callbacks import DashboardCallbacks
from ix.web.pages.dashboard.layout import layout

__all__ = [
    "DataManager",
    "BackgroundRefreshManager",
    "HeatmapGenerator",
    "ChartUtilities",
    "SkeletonLoader",
    "ErrorDisplay",
    "LayoutHelpers",
    "DashboardCallbacks",
    "layout",
]
