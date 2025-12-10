from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TodoItem(BaseModel):
    text: str
    completed: bool = False

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High)$")
    dueDate: datetime
    assignedTo: List[str]
    attachments: List[str] = []
    todoChecklist: List[TodoItem] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    dueDate: Optional[datetime] = None
    assignedTo: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    todoChecklist: Optional[List[TodoItem]] = None

class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(Pending|In Progress|Completed)$")

class ChecklistUpdate(BaseModel):
    todoChecklist: List[TodoItem]
