import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from . import routers

load_dotenv()

app = FastAPI()

# Include the routers
app.include_router(routers.data.router, prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current directory
current_dir = os.path.dirname(__file__)

# Mount static files under /_next/static (or other appropriate path)
app.mount(
    "/_next/static",
    StaticFiles(
        directory=os.path.abspath(os.path.join(current_dir, "out", "_next", "static"))
    ),
    name="static",
)

@app.get("/api/health")
async def health_check():
    try:
        # You can add more checks here, like database connectivity
        return JSONResponse(
            content={"status": "healthy"},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # List of extensions to check, in order of preference
    extensions = [".html", ".txt", ""]

    for ext in extensions:
        file_path = os.path.join(current_dir, "out", f"{full_path}{ext}")
        if os.path.isfile(file_path):
            return FileResponse(file_path)

    # If no matching file is found, serve the index.html
    index_path = os.path.join(current_dir, "out", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    # If even index.html is not found, raise a 404 error
    raise HTTPException(status_code=404, detail="File not found")
