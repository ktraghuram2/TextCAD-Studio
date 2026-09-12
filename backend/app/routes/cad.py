from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class CADRequest(BaseModel):
    code: str
    parameters: Optional[dict] = None

class CADResponse(BaseModel):
    status: str
    model_preview: Optional[str] = None
    info: dict

@router.post("/generate-from-code")
async def generate_from_code(request: CADRequest) -> CADResponse:
    """
    Generate CAD model directly from Python code
    """
    try:
        # Would get from app.state in real implementation
        cad_generator = None
        
        result = await cad_generator.generate_from_code(request.code)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        preview = await cad_generator.generate_stl_preview(result["model"])
        
        return CADResponse(
            status="success",
            model_preview=preview,
            info=result.get("info", {})
        )
    
    except Exception as e:
        logger.error(f"CAD generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-code")
async def validate_code(request: CADRequest) -> dict:
    """
    Validate CAD code syntax without execution
    """
    try:
        import ast
        ast.parse(request.code)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}
