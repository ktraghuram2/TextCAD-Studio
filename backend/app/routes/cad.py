from fastapi import APIRouter, HTTPException, Request
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
async def generate_from_code(cad_req: CADRequest, req: Request) -> CADResponse:
    """
    Generate CAD model directly from Python code
    """
    try:
        cad_generator = getattr(req.app.state, "cad_generator", None)
        if not cad_generator:
            raise HTTPException(status_code=503, detail="CAD Generator service not available")
        
        result = await cad_generator.generate_from_code(cad_req.code)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "CAD execution failed"))
        
        preview = await cad_generator.generate_stl_preview(result["model"])
        
        return CADResponse(
            status="success",
            model_preview=preview,
            info=result.get("info", {})
        )
    
    except HTTPException:
        raise
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
