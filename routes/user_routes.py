from fastapi import APIRouter, Depends, Request
from controllers.user_controller import *
from middlewares.auth_middleware import *

router = APIRouter(prefix="/api/users", tags=["Users"])

# Get all users (Admin Only)
@router.get("/")
async def fetch_users(request: Request, user=Depends(admin_only)):
    return await get_users()


# Get user by ID (Any logged-in user)
@router.get("/{id}")
async def fetch_user_by_id(id: str, request: Request, user=Depends(protect)):
    return await get_user_by_id(id)
