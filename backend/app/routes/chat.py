from fastapi import APIRouter, WebSocket, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    cad_code: Optional[str] = None
    design_history: Optional[List[str]] = None
    model_context: Optional[dict] = None

class ChatResponse(BaseModel):
    status: str
    message: str
    cad_code: Optional[str] = None
    model_preview: Optional[str] = None  # Base64 encoded STL
    design_id: Optional[str] = None

@router.post("/generate")
async def generate_cad_from_chat(chat_req: ChatRequest, req: Request) -> ChatResponse:
    """
    Generate CAD code from natural language chat message
    """
    try:
        llm_engine = getattr(req.app.state, "llm_engine", None)
        cad_generator = getattr(req.app.state, "cad_generator", None)

        cad_code = chat_req.cad_code
        if not cad_code and llm_engine:
            cad_code = await llm_engine.generate_cad_code(
                chat_req.message,
                chat_req.design_history
            )
        
        preview_stl = None
        if cad_generator and cad_code:
            execution_result = await cad_generator.generate_from_code(cad_code)
            if execution_result.get("success"):
                model = execution_result["model"]
                preview_stl = await cad_generator.generate_stl_preview(model)

        return ChatResponse(
            status="success",
            message="CAD model generated successfully",
            cad_code=cad_code,
            model_preview=preview_stl,
            design_id=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Chat generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat and model updates
    """
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            response = {
                "status": "received",
                "message": message.get("content", "")
            }
            
            await websocket.send_json(response)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)
