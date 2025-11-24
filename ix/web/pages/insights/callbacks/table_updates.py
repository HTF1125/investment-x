"""Table update callbacks."""

from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ix.web.pages.insights.components.table import create_insights_table
from ix.web.pages.insights.utils.data_utils import deserialize_insights, serialize_insights, filter_insights, sort_insights


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("total-count", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Input("filter-no-summary", "n_clicks"),
    State("no-summary-filter", "data"),
    State("insights-data", "data"),
    State("filter-state", "data"),
    State("page-size", "data"),
    prevent_initial_call=True,
)
def toggle_no_summary_filter(n_clicks, current_filter_state, insights_data, filter_state, page_size):
    """Toggle no-summary-only filter."""
    if not n_clicks:
        raise PreventUpdate

    # Toggle filter state
    new_filter_state = not (current_filter_state or False)

    # If we have stored filter state, we need to reload from database with filters
    if filter_state:
        from ix.db.client import get_insights
        from ix.web.pages.insights.utils.data_utils import normalize_insight_data

        # Reload with filters
        search_query = filter_state.get("search") or ""
        if search_query:
            insights_raw = get_insights(search=search_query, limit=10000)
        else:
            insights_raw = get_insights(limit=10000)

        insights_list = [normalize_insight_data(insight) for insight in insights_raw]

        # Apply all filters including no-summary
        filtered = filter_insights(
            insights_list,
            search=filter_state.get("search"),
            issuer=filter_state.get("issuer"),
            start_date=filter_state.get("start_date"),
            end_date=filter_state.get("end_date"),
            no_summary_only=new_filter_state,
        )

        if filter_state.get("sort"):
            filtered = sort_insights(filtered, filter_state.get("sort"))
    elif insights_data:
        # No stored filters, just filter current data
        insights_list = deserialize_insights(insights_data)

        if new_filter_state:
            filtered = [
                insight for insight in insights_list
                if not insight.get("summary") or not str(insight.get("summary", "")).strip()
            ]
        else:
            filtered = insights_list
    else:
        raise PreventUpdate

    if not filtered:
        from ix.web.pages.insights.callbacks.data_loading import create_empty_state
        empty = create_empty_state("No insights without summaries found.")
        serialized = serialize_insights(filtered) if filter_state else insights_data
        return empty, serialized, 0, 1, 1

    # Load first page
    page_size = page_size or 20
    insights_to_show = filtered[:page_size]
    table = create_insights_table(insights_to_show)

    # Serialize filtered data
    if filter_state:
        serialized_data = serialize_insights(filtered)
    else:
        serialized_data = serialize_insights(filtered) if filtered else insights_data

    total_count = len(filtered)
    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return table, serialized_data, total_count, total_pages, 1


@callback(
    Output("no-summary-filter", "data"),
    Output("filter-no-summary", "variant"),
    Input("filter-no-summary", "n_clicks"),
    State("no-summary-filter", "data"),
    prevent_initial_call=True,
)
def update_filter_button_state(n_clicks, current_state):
    """Update filter button visual state."""
    if not n_clicks:
        raise PreventUpdate

    new_state = not (current_state or False)
    variant = "filled" if new_state else "light"

    return new_state, variant


@callback(
    Output("insights-count-badge", "children"),
    Input("total-count", "data"),
)
def update_insights_count(total_count):
    """Update insights count badge."""
    if not total_count:
        return "0 documents"

    count = total_count if isinstance(total_count, int) else 0
    return f"{count} document{'s' if count != 1 else ''}"
