from fastapi import HTTPException
from config.database import database
from datetime import datetime
from fastapi import Request
from models.task_model import *
from bson import ObjectId
from utils.helper import populate_assigned_users
from websocket.manager import manager

tasks = database["tasks"]
users = database["users"]

# Admin Dashboard Data
async def get_dashboard_data():
    try:
        # BASIC STATISTICS
        total_tasks = await tasks.count_documents({})
        pending_tasks = await tasks.count_documents({"status": "Pending"})
        completed_tasks = await tasks.count_documents({"status": "Completed"})
        overdue_tasks = await tasks.count_documents({
            "status": {"$ne": "Completed"},
            "dueDate": {"$lt": datetime.utcnow()},
        })

        # TASK STATUS DISTRIBUTION
        task_statuses = ["Pending", "In Progress", "Completed"]

        rows = await tasks.aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]).to_list(length=None)

        task_distribution = {
            status.replace(" ", ""): next(
                (item["count"] for item in rows if item["_id"] == status),
                0
            )
            for status in task_statuses
        }

        task_distribution["All"] = total_tasks

        # TASK PRIORITY LEVELS
        priorities = ["Low", "Medium", "High"]

        rows2 = await tasks.aggregate([
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]).to_list(length=None)

        task_priority_levels = {
            p: next((item["count"] for item in rows2 if item["_id"] == p), 0)
            for p in priorities
        }

        # RECENT 10 TASKS
        recent_tasks = []
        async for t in tasks.find(
            {}, {"title": 1, "status": 1, "priority": 1, "dueDate": 1, "createdAt": 1}
        ).sort("createdAt", -1).limit(10):

            t["id"] = str(t["_id"])
            del t["_id"]
            recent_tasks.append(t)

        # RESPONSE
        return {
            "statistics": {
                "totalTasks": total_tasks,
                "pendingTasks": pending_tasks,
                "completedTasks": completed_tasks,
                "overdueTasks": overdue_tasks,
            },
            "charts": {
                "taskDistribution": task_distribution,
                "taskPriorityLevels": task_priority_levels,
            },
            "recentTasks": recent_tasks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User Dashboard Data
async def get_user_dashboard_data(request: Request):
    try:
        user_id = request.state.user["id"]

        # USER-SPECIFIC STATISTICS
        total_tasks = await tasks.count_documents({"assignedTo": user_id})
        pending_tasks = await tasks.count_documents({"assignedTo": user_id, "status": "Pending"})
        completed_tasks = await tasks.count_documents({"assignedTo": user_id, "status": "Completed"})
        overdue_tasks = await tasks.count_documents({
            "assignedTo":  ObjectId(user_id),
            "status": {"$ne": "Completed"},
            "dueDate": {"$lt": datetime.utcnow()},
        })

        # TASK STATUS DISTRIBUTION
        task_statuses = ["Pending", "In Progress", "Completed"]
        rows = await tasks.aggregate([
            {"$match": {"assignedTo": user_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]).to_list(length=None)

        task_distribution = {status.replace(" ", ""): next((item["count"] for item in rows if item["_id"] == status), 0)
                             for status in task_statuses}
        task_distribution["All"] = total_tasks

        # TASK PRIORITY LEVELS
        priorities = ["Low", "Medium", "High"]
        rows2 = await tasks.aggregate([
            {"$match": {"assignedTo": user_id}},
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]).to_list(length=None)

        task_priority_levels = {p: next((item["count"] for item in rows2 if item["_id"] == p), 0) for p in priorities}

        # Optional: fetch recent tasks (limit 5)
        recent_tasks_cursor = tasks.find({"assignedTo": user_id}).sort("dueDate", -1).limit(5)
        recent_tasks = []
        async for t in recent_tasks_cursor:
            t["id"] = str(t["_id"])
            t.pop("_id")
            recent_tasks.append(t)

        return {
            "statistics": {
                "totalTasks": total_tasks,
                "pendingTasks": pending_tasks,
                "completedTasks": completed_tasks,
                "overdueTasks": overdue_tasks,
            },
            "charts": {
                "taskDistribution": task_distribution,
                "taskPriorityLevels": task_priority_levels,
            },
            "recentTasks": recent_tasks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create Task (Admin only)
async def create_task(request: Request, data: TaskCreate):
    user = request.state.user

    # Validation
    if not isinstance(data.assignedTo, list):
        raise HTTPException(status_code=400, detail="assignedTo must be an array")

    task_doc = {
        "title": data.title,
        "description": data.description,
        "priority": data.priority,
        "dueDate": data.dueDate,
        "assignedTo": data.assignedTo,      # store strings
        "createdBy": user["id"],            # simple string
        "attachments": data.attachments,
        "todoChecklist": [item.model_dump() for item in data.todoChecklist],  # Pydantic v2
        "status": "Pending",
        "progress": 0,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    # Insert into MongoDB
    result = await tasks.insert_one(task_doc)

    # Add id field
    task_doc["id"] = str(result.inserted_id)

    for user_id in data.assignedTo:
        await manager.send_to_user(
            user_id,
            {
                "type": "TASK_ASSIGNED",
                "taskId": str(result.inserted_id),
                "title": data.title,
                "message": "A new task has been assigned to you"
            }
        )
        print("🟢 WebSocket connected:", user_id)


    # Remove raw MongoDB _id before returning
    if "_id" in task_doc:
        del task_doc["_id"]

    # Convert datetime to string for safety
    task_doc["createdAt"] = task_doc["createdAt"].isoformat()
    task_doc["updatedAt"] = task_doc["updatedAt"].isoformat()

    return {
        "message": "Task created successfully",
        "task": task_doc
    }

# List Tasks (Admin or User)
async def get_tasks(request: Request, status: str = None):
    user = request.state.user

    filter_query = {}
    if status:
        filter_query["status"] = status

    # ADMIN → ALL TASKS
    if user["role"] == "admin":
        cursor = tasks.find(filter_query)
        base_filter = {}

    else:
        # USER → MATCH ARRAY CONTAINS (same as Mongoose)
        cursor = tasks.find({
            **filter_query,
            "assignedTo": {"$in": [user["id"]]}
        })
        base_filter = {"assignedTo": {"$in": [user["id"]]}}

    task_list = []
    async for task in cursor:
        task["_id"] = str(task["_id"])  # keep _id
        task["assignedTo"] = await populate_assigned_users(task)

        # Completed checklist
        task["completedTodoCount"] = sum(
            1 for item in task.get("todoChecklist", []) if item.get("completed")
        )

        task_list.append(task)

    # --- STATUS SUMMARY ---
    all_tasks = await tasks.count_documents(base_filter)

    pending_tasks = await tasks.count_documents({
        **base_filter,
        "status": "Pending"
    })
    in_progress = await tasks.count_documents({
        **base_filter,
        "status": "In Progress"
    })
    completed = await tasks.count_documents({
        **base_filter,
        "status": "Completed"
    })

    return {
        "tasks": task_list,
        "statusSummary": {
            "all": all_tasks,
            "pendingTasks": pending_tasks,
            "inProgressTasks": in_progress,
            "completedTasks": completed
        }
    }


# Get Task by ID (Admin or User)
async def get_task_by_id(task_id: str):
    try:
        oid = ObjectId(task_id)
    except:
        raise HTTPException(400, "Invalid task id")

    task = await tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(404, "Task not found")

    task["_id"] = str(task["_id"])  # keep _id
    task["assignedTo"] = await populate_assigned_users(task)

    return task

# Update Task (Admin only)
async def update_task(task_id: str, data: TaskUpdate):
    task = await tasks.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(404, "Task not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    # Check for todo list update
    is_todo_updated = "todoChecklist" in update_data and update_data["todoChecklist"] is not None

    if is_todo_updated:
        # Convert checklist items to dict
        checklist = [item.model_dump() for item in data.todoChecklist]

        # Recalculate progress after admin adds new todos
        completed = sum(1 for c in checklist if c["completed"])
        total = len(checklist)

        progress = round((completed / total) * 100) if total > 0 else 0
        update_data["progress"] = progress

        # Admin adding new items → some will be incomplete → so status = In Progress
        if progress == 100:
            update_data["status"] = "Completed"
        elif progress > 0:
            update_data["status"] = "In Progress"
        else:
            update_data["status"] = "Pending"

        update_data["todoChecklist"] = checklist

    # Convert assignedTo to string list
    if "assignedTo" in update_data:
        update_data["assignedTo"] = update_data["assignedTo"]

    # Update time
    update_data["updatedAt"] = datetime.utcnow()

    await tasks.update_one({"_id": ObjectId(task_id)}, {"$set": update_data})

    updated_task = await tasks.find_one({"_id": ObjectId(task_id)})

    # Convert id for frontend
    updated_task["_id"] = str(updated_task["_id"])
    updated_task["id"] = updated_task["_id"]

    return {
        "message": "Task updated successfully",
        "task": updated_task
    }

# Delete Task (Admin only)
async def delete_task(task_id: str):
    try:
        oid = ObjectId(task_id)
    except:
        raise HTTPException(400, "Invalid task id")

    task = await tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(404, "Task not found")

    await tasks.delete_one({"_id": oid})

    return {"message": "Task deleted successfully"}

# Update Task Checklist (Assigned User or Admin)
async def update_task_checklist(request: Request, task_id: str, data: ChecklistUpdate):
    user = request.state.user

    try:
        oid = ObjectId(task_id)
    except:
        raise HTTPException(400, "Invalid task id")

    task = await tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(404, "Task not found")

    if user["id"] not in task["assignedTo"] and user["role"] != "admin":
        raise HTTPException(403, "Not authorized")

    checklist = [item.model_dump() for item in data.todoChecklist]

    # calculate progress
    total = len(checklist)
    completed = sum(1 for i in checklist if i["completed"])
    progress = round((completed / total) * 100) if total > 0 else 0

    status = (
        "Completed" if progress == 100
        else "In Progress" if progress > 0
        else "Pending"
    )

    update = {
        "todoChecklist": checklist,
        "progress": progress,
        "status": status,
        "updatedAt": datetime.utcnow()
    }

    await tasks.update_one({"_id": oid}, {"$set": update})

    updated = await tasks.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    # del updated["_id"]

    return {"message": "Task checklist updated successfully", "task": updated}
