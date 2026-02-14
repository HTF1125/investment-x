# Serve SPA - Static Files
# Only if 'static' directory exists (e.g. in Docker)
import os

static_dir = os.path.join(os.getcwd(), "static")
if os.path.exists(static_dir):
    logger.info(f"Serve static frontend from {static_dir}")

    # Mount /_next first
    app.mount(
        "/_next",
        StaticFiles(directory=os.path.join(static_dir, "_next")),
        name="next_assets",
    )

    # Catch-all for other static files or SPA index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html
        return FileResponse(os.path.join(static_dir, "index.html"))

else:
    logger.info("Static directory not found, running API only mode")
