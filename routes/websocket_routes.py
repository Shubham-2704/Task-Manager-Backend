from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket.manager import manager
from utils.auth import decode_token

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user = decode_token(token)
    user_id = user["id"]

    await manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
