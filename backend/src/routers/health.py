from fastapi import APIRouter

router = APIRouter(
    prefix="/api/health",
    tags=["Health Check"]
)


@router.get("")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Service is running"}
