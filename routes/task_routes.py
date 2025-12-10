from fastapi import APIRouter, Depends, Request
from controllers.task_controller import *
from models.task_model import *
from middlewares.auth_middleware import protect, admin_only

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# ADMIN DASHBOARD DATA
@router.get("/dashboard-data")
async def dashboard_data(
    request: Request,
    user = Depends(admin_only)
):
    return await get_dashboard_data()

# USER DASHBOARD DATA
@router.get("/user-dashboard-data")
async def user_dashboard(
    request: Request,
    user = Depends(protect)
):
    return await get_user_dashboard_data(request)

# GET ALL TASKS (Admin: All, User: Assigned)
@router.get("/")
async def list_tasks(
    request: Request,
    status: str = None,   
    user = Depends(protect)
):
    return await get_tasks(request,status)

# GET TASK BY ID
@router.get("/{task_id}")
async def task_by_id(
    task_id: str,
    request: Request,
    user = Depends(protect)
):
    return await get_task_by_id(task_id)

# CREATE TASK (Admin only)
@router.post("/")
async def create_new_task(
    data: TaskCreate,
    request: Request,
    user = Depends(admin_only)
):
    return await create_task(request, data)

# UPDATE TASK (Admin only)
@router.put("/{task_id}")
async def update_task_route(
    task_id: str,
    data: TaskUpdate,
    user = Depends(protect)
):
    return await update_task(task_id, data)

# DELETE TASK (Admin only)
@router.delete("/{task_id}")
async def delete_task_route(
    task_id: str,
    request: Request,
    user = Depends(admin_only)
):
    return await delete_task(task_id)

# UPDATE CHECKLIST
@router.put("/{task_id}/todo")
async def update_checklist(
    task_id: str,
    data: ChecklistUpdate,
    request: Request,
    user = Depends(protect)
):
    return await update_task_checklist(request, task_id, data)
