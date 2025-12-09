from fastapi import Request, Depends
from middlewares.auth_middleware import protect
from config.database import database
from bson import ObjectId
from models.user_model import *
from utils.hash import hash_password, verify_password
from utils.auth import generate_token
from utils.helper import *
import os
from datetime import datetime

users = database["users"]

# Register User
async def register_user(data: UserCreate):
    user_exists = await users.find_one({"email": data.email})
    if user_exists:
        return error_response(400, "User with this email already exists")

    # Role Logic 
    role = "member"
    if data.adminInviteToken and data.adminInviteToken == os.getenv("ADMIN_INVITE_TOKEN"):
        role = "admin"

    hashed_pw = hash_password(data.password)

    now = datetime.now(timezone.utc) 
    new_user = {
        "name": data.name,
        "email": data.email,
        "password": hashed_pw,
        "profileImageUrl": data.profileImageUrl,
        "role": role,
        "createdAt": now, 
        "updatedAt": now
    }

    result = await users.insert_one(new_user)
    user_id = str(result.inserted_id)

    return UserResponse(
        id=user_id,
        name=data.name,
        email=data.email,
        profileImageUrl=data.profileImageUrl,
        role=role,
        token=generate_token(user_id),
        createdAt=now,
        updatedAt=now
    )


# Login User
async def login_user(data: UserLogin):
    user = await users.find_one({"email": data.email})
    if not user:
        return error_response(401, "Invalid email or password")

    if not verify_password(data.password, user["password"]):
       return error_response(401, "Invalid email or password")

    now = datetime.now(timezone.utc) 
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        profileImageUrl=user.get("profileImageUrl"),
        role=user["role"],
        token=generate_token(str(user["_id"])),
        updatedAt=now
    )


# Get User Profile
async def get_profile(request: Request, user_data=Depends(protect)):
    user_id = request.state.user["id"] 

    user = await users.find_one({"_id": ObjectId(user_id)}, {"password": 0})

    if not user:
        return error_response(404, "User not found")

    user["_id"] = str(user["_id"]) 
 
    return user
