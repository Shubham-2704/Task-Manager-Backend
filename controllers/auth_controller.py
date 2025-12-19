from fastapi import Request, Depends
from middlewares.auth_middleware import protect
from config.database import database
from bson import ObjectId
from models.user_model import *
from utils.hash import hash_password, verify_password
from utils.auth import generate_token
from utils.helper import *
import os
from datetime import datetime, timedelta
from utils.email import *
from utils.otp import *
from utils.hash import *

users = database["users"]
reset_otps = database["password_reset_otps"]

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

async def update_profile(request: Request, data: UserUpdate, user_data=Depends(protect)):
    user_id = request.state.user["id"]

    update_data = {
        "updatedAt": datetime.now(timezone.utc)
    }

    # update only if image is provided
    if data.profileImageUrl is not None:
        update_data["profileImageUrl"] = data.profileImageUrl

    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )

    user = await users.find_one({"_id": ObjectId(user_id)})
    print("Updated User:", user)

    return {
        "message": "Profile updated Successfully",
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "profileImageUrl": user.get("profileImageUrl"),
        "updatedAt": user.get("updatedAt")
    }

async def forgot_password(data: ForgotPasswordRequest):
    user = await users.find_one({"email": data.email})
    if not user:
        return error_response(404, "User not found")

    now = datetime.now(timezone.utc)

    # 🛑 BLOCK CHECK
    existing = await reset_otps.find_one({"userId": user["_id"]})
    if existing and existing.get("blockedUntil"):
        blocked_until = existing["blockedUntil"]
        if blocked_until.tzinfo is None:
            blocked_until = blocked_until.replace(tzinfo=timezone.utc)

        if now < blocked_until:
            minutes_left = int((blocked_until - now).total_seconds() / 60)
            return error_response(
                429,
                f"Too many attempts. Try again after {minutes_left} minutes"
            )

    otp = generate_otp()
    now = datetime.now(timezone.utc)

    await reset_otps.update_one(
        {"userId": user["_id"]},
        {
            "$set": {
                "userId": user["_id"],
                "email": user["email"],
                "otp": hash_password(otp),
                "expiresAt": now + timedelta(minutes=5),  # ✅ 5 MIN
                "attempts": 0,
                "blockedUntil": None,
                "createdAt": now
            }
        },
        upsert=True
    )

    send_otp_email(
        to_email=user["email"],
        user_name=user["name"],
        otp=otp,
        expiry_minutes=5
    )

    return {
        "message": "OTP sent to your email",
        "expiresIn": 30  # seconds
    }

MAX_ATTEMPTS = 3
BLOCK_DURATION = timedelta(hours=1)

async def verify_reset_otp(data: VerifyOtpRequest):
    record = await reset_otps.find_one({"email": data.email})
    if not record:
        return error_response(400, "OTP expired or invalid")

    now = datetime.now(timezone.utc)

    # 🛑 BLOCK CHECK
    blocked_until = record.get("blockedUntil")
    if blocked_until:
        if blocked_until.tzinfo is None:
            blocked_until = blocked_until.replace(tzinfo=timezone.utc)

        if now < blocked_until:
            minutes_left = int((blocked_until - now).total_seconds() / 60)
            return error_response(
                429,
                f"Try again after {minutes_left} minutes"
            )

    # ❌ WRONG OTP
    if not verify_password(data.otp, record["otp"]):
        attempts = record.get("attempts", 0) + 1
        update = {"attempts": attempts}

        if attempts >= MAX_ATTEMPTS:
            update["blockedUntil"] = now + BLOCK_DURATION


        await reset_otps.update_one(
            {"_id": record["_id"]},
            {"$set": update}
        )

        return error_response(400, "Invalid OTP try again")

    return success_response("OTP verified successfully")

async def reset_password(data: ResetPasswordRequest):
    record = await reset_otps.find_one({"email": data.email})
    if not record:
        return error_response(400, "OTP expired")

    if not verify_password(data.otp, record["otp"]):
        return error_response(400, "Invalid OTP")

    await users.update_one(
        {"email": data.email},
        {"$set": {
            "password": hash_password(data.newPassword),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    # 🧹 DELETE OTP RECORD
    await reset_otps.delete_one({"_id": record["_id"]})

    return success_response("Password reset successfully")
