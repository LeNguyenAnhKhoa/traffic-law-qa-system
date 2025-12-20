import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from root .env and backend .env
root_env = Path(__file__).parent.parent / ".env"
backend_env = Path(__file__).parent / ".env"
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

from src import config
from src.routers import health as health_route
from src.routers import agent as agent_route

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Traffic Law QA System",
    description="AI agent to handle traffic law related questions.",
    version=config.API_VERSION,
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
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
