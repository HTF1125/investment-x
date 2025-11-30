"""Drag and drop visual feedback callbacks."""

from dash import clientside_callback, Input, Output


# Add drag and drop visual feedback (without interfering with dcc.Upload handling)
clientside_callback(
    """
    function(upload_zone_rendered) {
        // Wait for DOM to be ready
        setTimeout(function() {
            const uploadZone = document.querySelector('.pdf-upload-zone');
            if (!uploadZone) return;

            // Skip if already initialized
            if (uploadZone.dataset.dragdropInitialized === 'true') return;
            uploadZone.dataset.dragdropInitialized = 'true';

            // Prevent page from opening files when dropping outside the zone
            ['dragenter', 'dragover'].forEach(eventName => {
                document.addEventListener(eventName, function(e){ e.preventDefault(); }, false);
            });
            document.addEventListener('drop', function(e){
                if (!e.target.closest('.pdf-upload-zone')) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }, false);

            // Add visual feedback when dragging over
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadZone.addEventListener(eventName, function(e) {
                    e.preventDefault(); // allow drop
                    uploadZone.classList.add('drag-over');
                }, false);
            });

            // Remove visual feedback when dragging leaves
            ['dragleave', 'drop'].forEach(eventName => {
                uploadZone.addEventListener(eventName, function(e) {
                    uploadZone.classList.remove('drag-over');
                }, false);
            });
        }, 300);

        return window.dash_clientside.no_update;
    }
    """,
    Output("dragdrop-handler", "children"),
    Input("upload-pdf-dragdrop", "id"),
)
