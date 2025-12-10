from fastapi import HTTPException, Response
from config.database import database
from bson import ObjectId
from openpyxl import Workbook
from utils.helper import *

tasks = database["tasks"]
users = database["users"]

async def export_tasks_report():
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Tasks Report"

        # Header
        ws.append([
            "Task ID", "Title", "Description", "Priority",
            "Status", "Due Date", "Assigned To"
        ])

        cursor = tasks.find({})
        async for task in cursor:
            task_id = str(task["_id"])

            # Populate assigned users
            assigned_users = []
            for uid in task.get("assignedTo", []):
                if ObjectId.is_valid(uid):
                    user = await users.find_one({"_id": ObjectId(uid)})
                    if user:
                        assigned_users.append(f"{user.get('name')} ({user.get('email')})")

            assigned_str = ", ".join(assigned_users) if assigned_users else "Unassigned"

            ws.append([
                task_id,
                task.get("title"),
                task.get("description"),
                task.get("priority"),
                task.get("status"),
                task.get("dueDate").strftime("%Y-%m-%d") if task.get("dueDate") else "",
                assigned_str
            ])

        # Prepare file for response
        file_bytes = save_workbook_to_bytes(wb)

        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=tasks_report.xlsx"
            }
        )

    except Exception as e:
        raise HTTPException(500, f"Error exporting tasks: {str(e)}")

async def export_users_report():
    try:
        # Fetch all users
        user_list = []
        async for u in users.find({}, {"name": 1, "email": 1}):
            user_list.append({
                "id": str(u["_id"]),
                "name": u.get("name"),
                "email": u.get("email")
            })

        # Fetch all tasks
        task_cursor = tasks.find({})
        task_list = [t async for t in task_cursor]

        # Build user task statistics
        stats = {}
        for u in user_list:
            stats[u["id"]] = {
                "name": u["name"],
                "email": u["email"],
                "taskCount": 0,
                "pendingTasks": 0,
                "inProgressTasks": 0,
                "completedTasks": 0,
            }

        # Count tasks
        for t in task_list:
            for uid in t.get("assignedTo", []):
                if uid in stats:
                    stats[uid]["taskCount"] += 1

                    if t["status"] == "Pending":
                        stats[uid]["pendingTasks"] += 1
                    elif t["status"] == "In Progress":
                        stats[uid]["inProgressTasks"] += 1
                    elif t["status"] == "Completed":
                        stats[uid]["completedTasks"] += 1

        # Create Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "User Task Report"

        ws.append([
            "User Name", "Email", "Total Assigned Tasks",
            "Pending Tasks", "In Progress Tasks", "Completed Tasks"
        ])

        for u in stats.values():
            ws.append([
                u["name"], u["email"], u["taskCount"],
                u["pendingTasks"], u["inProgressTasks"], u["completedTasks"]
            ])

        file_bytes = save_workbook_to_bytes(wb)

        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=users_report.xlsx"
            }
        )

    except Exception as e:
        raise HTTPException(500, f"Error exporting users: {str(e)}")
