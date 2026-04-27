"""
Auth routes for the AI Forex Trading Bot.
Handles user authentication via Supabase Auth.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from models import UserCreate, UserLogin, User
from services.supabase_service import supabase_service
from utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/register")
async def register(user_data: UserCreate):
    """
    Register a new user.
    
    Note: In production, use Supabase client-side SDK for auth
    and verify JWT tokens server-side.
    """
    try:
        # In production, you would use Supabase Auth API directly
        # This is a simplified version
        
        import uuid
        user_id = str(uuid.uuid4())
        
        # Create user record in database
        user = await supabase_service.create_user(user_data.email, user_id)
        
        if not user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        logger.info(f"User registered: {user.email}")
        
        return {
            "status": "success",
            "user_id": user.id,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(credentials: UserLogin):
    """
    Login user.
    
    Note: In production, use Supabase Auth with proper JWT handling.
    """
    try:
        # In production, authenticate with Supabase Auth API
        # This is a simplified mock implementation
        
        # For demo purposes, we'll create/find user by email
        # In real app, verify password with Supabase Auth
        
        import uuid
        # Generate deterministic ID from email for demo
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, credentials.email))
        
        user = await supabase_service.get_user(user_id)
        
        if not user:
            # Create user on first login (demo mode)
            user = await supabase_service.create_user(credentials.email, user_id)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate a mock token (in production, get real JWT from Supabase)
        token = f"mock_token_{user_id}"
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Get current authenticated user from token.
    
    Returns user_id if authenticated, None otherwise.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # In production, verify JWT token with Supabase
    # For demo, extract user_id from mock token
    if token.startswith("mock_token_"):
        user_id = token.replace("mock_token_", "")
        return user_id
    
    return None


@router.get("/me")
async def get_current_user_info(
    user_id: Optional[str] = Depends(get_current_user)
):
    """Get current user information."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = await supabase_service.get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
