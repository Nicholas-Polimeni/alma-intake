from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_settings

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the API token for protected endpoints.
    
    Args:
        credentials: The bearer token from the Authorization header
        
    Returns:
        True if token is valid
        
    Raises:
        HTTPException if token is invalid
    """
    expected_token = os.getenv("API_SECRET_TOKEN")
    
    if not expected_token:
        # fail if no token configured
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True