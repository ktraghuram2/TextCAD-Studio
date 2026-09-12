from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import logging

from app.routes import chat, cad, export
from app.services.llm_engine import LLMEngine
from app.services.cad_generator import CADGenerator

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TextCAD-Studio API",
    description="AI-powered Text-to-CAD generation platform",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_engine = LLMEngine()
cad_generator = CADGenerator()

# Store in app state for dependency injection
app.state.llm_engine = llm_engine
app.state.cad_generator = cad_generator

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(cad.router, prefix="/api/cad", tags=["cad"])
app.include_router(export.router, prefix="/api/export", tags=["export"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting TextCAD-Studio API...")
    logger.info(f"LLM Provider: {os.getenv('LLM_PROVIDER', 'gemini')}")
    logger.info(f"CORS Origin: {os.getenv('CORS_ORIGINS', 'http://localhost:3000')}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down TextCAD-Studio API...")

@app.get("/")
async def root():
    return {
        "name": "TextCAD-Studio API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat/generate",
            "cad": "/api/cad/generate",
            "export": "/api/export/stl",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
