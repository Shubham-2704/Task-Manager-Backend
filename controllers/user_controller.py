from fastapi import HTTPException
from bson import ObjectId
from config.database import database

users = database["users"]
tasks = database["tasks"]

# Get all users (Admin-only)
async def get_users():
    # Find all member role users
    cursor = users.find({"role": "member"},{"password": 0})  # hide password
    user_list = await cursor.to_list(length=None)
    # print(user_list)

    result = []

    for user in user_list:
        user_id = str(user["_id"])

        # Count tasks
        pending = await tasks.count_documents({"assignedTo": user_id, "status": "Pending"})
        in_progress = await tasks.count_documents({"assignedTo": user_id, "status": "In Progress"})
        completed = await tasks.count_documents({"assignedTo": user_id, "status": "Completed"})

        result.append({
            "_id": user_id,
            "name": user["name"],
            "email": user["email"],
            "profileImageUrl": user.get("profileImageUrl"),
            "role": user["role"],
            "pendingTasks": pending,
            "inProgressTasks": in_progress,
            "completedTasks": completed,
        })

    return result


# Get user by ID
async def get_user_by_id(user_id: str):
    user = await users.find_one({"_id": ObjectId(user_id)}, {"password": 0})

    if not user:
        raise HTTPException(404, "User not found")

    user["id"] = str(user["_id"])
    del user["_id"]

    return user

# Delete user by ID
async def delete_user(user_id: str):
    user = await users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(404, "User not found")

    await users.delete_one({"_id": ObjectId(user_id)})

    return {"message": "User deleted successfully"}
