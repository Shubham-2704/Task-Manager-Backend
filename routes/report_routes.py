from fastapi import APIRouter, Depends, Request
from controllers.report_controller import *
from middlewares.auth_middleware import protect

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/export/tasks")
async def export_tasks_report_route(
    request: Request,
    user = Depends(protect),
):
    return await export_tasks_report()

@router.get("/export/users")
async def export_users_report_route(
    request: Request,
    user = Depends(protect),
):
    return await export_users_report()