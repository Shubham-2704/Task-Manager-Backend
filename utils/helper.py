from fastapi.responses import JSONResponse
from config.database import database
from bson import ObjectId

users = database["users"]

def success_response(message: str, data=None, status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": data
        }
    )

def error_response(status_code: int, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"message": message}
    )

async def populate_assigned_users(task):
    populated = []

    for uid in task.get("assignedTo", []):
        if ObjectId.is_valid(uid):
            user = await users.find_one({"_id": ObjectId(uid)})
        else:
            user = None

        if user: 
            populated.append({
                "_id": str(user["_id"]),
                "name": user.get("name"),
                "email": user.get("email"),
                "profileImageUrl": user.get("profileImageUrl")
            })
        else:
            populated.append({"_id": uid})  # fallback

    return populated
