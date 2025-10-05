# Dashboard Module Structure

This dashboard has been refactored into a modular structure for better maintainability and readability.

## File Structure

```
ix/web/pages/dashboard/
├── __init__.py              # Module exports and initialization
├── layout.py               # Main dashboard layout and page registration
├── data_manager.py         # Data loading, caching, and background refresh
├── visualizations.py       # Heatmap generation and chart utilities
├── ui_components.py        # Skeleton loaders, error displays, layout helpers
├── callbacks.py           # Dashboard callbacks and event handlers
└── README.md              # This documentation
```

## Module Responsibilities

### data_manager.py

- **DataManager**: Handles data loading, caching, and retrieval
- **BackgroundRefreshManager**: Manages background data refresh operations
- Contains all database interactions and data processing logic

### visualizations.py

- **HeatmapGenerator**: Creates performance heatmaps with optimized rendering
- **ChartUtilities**: Provides utility functions for chart formatting and styling
- Handles all visualization-related logic

### ui_components.py

- **SkeletonLoader**: Creates loading animations for dashboard components
- **ErrorDisplay**: Generates error messages and retry interfaces
- **LayoutHelpers**: Provides reusable layout components and styling helpers

### callbacks.py

- **DashboardCallbacks**: Manages all dashboard callbacks and event handlers
- Handles data refresh, chart loading, and user interactions
- Centralizes all callback logic for better organization

### layout.py

- Main dashboard layout definition
- Page registration with Dash
- Imports and uses components from other modules
- Clean and minimal structure

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a clear, single responsibility
2. **Maintainability**: Easier to find and modify specific functionality
3. **Reusability**: Components can be easily reused across different pages
4. **Testability**: Individual modules can be tested in isolation
5. **Readability**: Much easier to understand and navigate the codebase
6. **Scalability**: New features can be added without cluttering existing files

## Usage

The dashboard maintains the same functionality as before but with improved organization:

- Data loading and caching is handled by `DataManager`
- Visualizations are created by `HeatmapGenerator`
- UI components are provided by utility classes
- All callbacks are registered through `DashboardCallbacks`

The main `layout.py` file now serves as a clean entry point that orchestrates all these components.
