from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.utils.logging_config import configure_logging
from src.routers import health as health_route
from src.routers import agent as agent_route

# Configure logging
configure_logging()

app = FastAPI(
    title="Traffic Law QA System",
    description="AI agent to handle traffic law related questions.",
    version=settings.API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_route.router)
app.include_router(agent_route.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.BACKEND_PORT)

