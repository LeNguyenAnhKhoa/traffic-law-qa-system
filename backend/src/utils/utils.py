from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from src.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


async def verify_token(token: str = Depends(oauth2_scheme)) -> bool:
    if token:
        if settings.SERVER_API_KEY == token:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provide API key",
        )

