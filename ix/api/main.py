import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager

from ix import task
from ix.api import routers

load_dotenv()

# Create a scheduler
scheduler = AsyncIOScheduler()


# Define your scheduled task
async def scheduled_task():
    task.run()


# Set up the lifespan event to start and stop the scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when the app starts
    scheduler.start()
    yield
    # Shut down the scheduler when the app stops
    scheduler.shutdown()


# Create the FastAPI app with the lifespan
app = FastAPI(lifespan=lifespan)
# Add the job to the scheduler
scheduler.add_job(scheduled_task, IntervalTrigger(hours=1))
app.include_router(routers.data.router, prefix="/api")
app.include_router(routers.admin.router, prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    try:
        # You can add more checks here, like database connectivity
        return JSONResponse(content={"status": "healthy"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
