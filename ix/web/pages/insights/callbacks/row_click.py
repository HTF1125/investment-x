"""Row click handler to open PDFs in new window."""

from dash import clientside_callback, Input, Output


# Add click handlers to table rows
clientside_callback(
    """
    function(table_children) {
        // Wait a bit for table to render
        setTimeout(function() {
            const rows = document.querySelectorAll('.insight-table-row');
            rows.forEach(function(row) {
                // Skip if already has listener
                if (row.dataset.clickHandlerAdded) {
                    return;
                }

                row.dataset.clickHandlerAdded = 'true';

                // Add click listener
                row.addEventListener('click', function(e) {
                    // Don't trigger if clicking on a link or button
                    if (e.target.tagName === 'A' || e.target.closest('a') ||
                        e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                        return;
                    }

                    const insightId = row.getAttribute('data-insight-id');
                    if (insightId) {
                        const pdfUrl = '/api/download-pdf/' + insightId;
                        window.open(pdfUrl, '_blank');
                    }
                });
            });
        }, 200);

        return window.dash_clientside.no_update;
    }
    """,
    Output("row-click-handler", "data"),
    Input("insights-table-container", "children"),
)
