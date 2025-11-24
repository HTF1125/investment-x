"""Drag and drop visual feedback callbacks."""

from dash import clientside_callback, Input, Output


# Add drag and drop visual feedback
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

            // Prevent default drag behaviors on the document
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                document.addEventListener(eventName, preventDefaults, false);
                uploadZone.addEventListener(eventName, preventDefaults, false);
            });

            // Add visual feedback when dragging over
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadZone.addEventListener(eventName, function(e) {
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
    Output("dragdrop-handler", "data"),
    Input("upload-pdf-dragdrop", "id"),
)
