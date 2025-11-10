import os
from fastapi import HTTPException, Header, Depends
from typing import Optional


def get_api_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and validate API token from Authorization header.

    Args:
        authorization: The Authorization header value

    Returns:
        The validated API token

    Raises:
        HTTPException: If token is missing, invalid format, or doesn't match
    """
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Authorization header is required", headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if it's a Bearer token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme. Use Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get expected token from environment
    expected_token = os.getenv("API_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="API token not configured on server")

    # Validate token
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid API token", headers={"WWW-Authenticate": "Bearer"})

    return token


def require_auth():
    """
    Dependency to require authentication for protected routes.
    """
    return Depends(get_api_token)
