from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ExportRequest(BaseModel):
    model_id: str
    format: str  # "stl", "step", "dxf"
    filename: Optional[str] = None

@router.post("/stl")
async def export_stl(request: ExportRequest) -> FileResponse:
    """
    Export model to STL format
    """
    try:
        # Would retrieve model from cache/db in real implementation
        filename = request.filename or f"{request.model_id}.stl"
        
        # Return file
        return FileResponse(
            path=filename,
            media_type="application/octet-stream",
            filename=filename
        )
    except Exception as e:
        logger.error(f"STL export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step")
async def export_step(request: ExportRequest) -> FileResponse:
    """
    Export model to STEP format
    """
    try:
        filename = request.filename or f"{request.model_id}.step"
        
        return FileResponse(
            path=filename,
            media_type="application/octet-stream",
            filename=filename
        )
    except Exception as e:
        logger.error(f"STEP export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
