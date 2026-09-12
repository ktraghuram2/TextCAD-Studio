import asyncio
import tempfile
import os
from typing import Optional, Dict, Any, Tuple
import logging
import io
import base64

try:
    from build123d import *
    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

import trimesh

logger = logging.getLogger(__name__)

class CADExecutor:
    """Safe execution of generated CAD code"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.max_size = int(os.getenv("MAX_MODEL_SIZE", 100000000))  # 100MB default
    
    async def execute(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Safely execute CAD generation code
        Returns: {"success": bool, "model": object, "error": str, "info": dict}
        """
        try:
            # Create isolated execution environment
            namespace = {
                "build123d": __import__("build123d") if BUILD123D_AVAILABLE else None,
                "cadquery": __import__("cadquery") if CADQUERY_AVAILABLE else None,
            }
            
            # Clean code
            code = code.strip()
            if code.startswith("```"):
                code = "\n".join(code.split("\n")[1:-1])
            
            # Execute with timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._execute_sync, code, namespace),
                timeout=self.timeout
            )
            
            return result
        
        except asyncio.TimeoutError:
            logger.error("CAD code execution timeout")
            return {
                "success": False,
                "error": f"Execution timeout (>{self.timeout}s)",
                "model": None
            }
        except Exception as e:
            logger.error(f"CAD execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": None
            }
    
    def _execute_sync(self, code: str, namespace: dict) -> Dict[str, Any]:
        """Synchronous execution"""
        try:
            exec(code, namespace)
            
            # Extract the created object
            model = None
            if "result" in namespace:
                model = namespace["result"]
            elif "part" in namespace:
                model = namespace["part"]
            elif "obj" in namespace:
                model = namespace["obj"]
            
            if model is None:
                return {"success": False, "error": "No CAD object created", "model": None}
            
            return {
                "success": True,
                "model": model,
                "error": None,
                "info": {"type": type(model).__name__}
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": None
            }

class CADGenerator:
    """Main CAD generation orchestrator"""
    
    def __init__(self):
        self.executor = CADExecutor()
        self.cache: Dict[str, Any] = {}
        logger.info(f"CAD Generator initialized. Build123d: {BUILD123D_AVAILABLE}, CadQuery: {CADQUERY_AVAILABLE}")
    
    async def generate_from_code(self, code: str) -> Dict[str, Any]:
        """Execute CAD code and return model"""
        result = await self.executor.execute(code)
        return result
    
    async def generate_stl_preview(self, model: Any) -> str:
        """Convert model to STL and return as base64"""
        try:
            # Convert to mesh
            if BUILD123D_AVAILABLE and hasattr(model, "to_mesh"):
                mesh_data = model.to_mesh()
            elif CADQUERY_AVAILABLE and hasattr(model, "val"):
                # CadQuery object
                shape = model.val
                mesh_data = self._cadquery_to_mesh(shape)
            else:
                return None
            
            # Convert to STL bytes
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
                if isinstance(mesh_data, trimesh.Trimesh):
                    mesh_data.export(tmp.name)
                else:
                    # Handle raw triangle data
                    mesh = trimesh.Trimesh(vertices=mesh_data["vertices"], faces=mesh_data["faces"])
                    mesh.export(tmp.name)
                
                with open(tmp.name, "rb") as f:
                    stl_bytes = f.read()
                
                os.unlink(tmp.name)
            
            # Encode to base64
            return base64.b64encode(stl_bytes).decode("utf-8")
        
        except Exception as e:
            logger.error(f"STL preview generation error: {e}")
            return None
    
    def _cadquery_to_mesh(self, shape) -> Dict[str, Any]:
        """Convert CadQuery shape to mesh data"""
        # This is a simplified approach - in production, use OCP's tessellation
        try:
            from OCP.StlAPI import StlAPI_Writer
            from OCP.Poly import Poly_Triangulation
            
            with tempfile.NamedTemporaryFile(suffix=".stl") as tmp:
                StlAPI_Writer.Write_s(shape, tmp.name, True)
                mesh = trimesh.load(tmp.name)
                return {
                    "vertices": mesh.vertices,
                    "faces": mesh.faces
                }
        except Exception as e:
            logger.error(f"Shape to mesh conversion failed: {e}")
            return None
    
    async def export_to_step(self, model: Any, filename: str) -> bool:
        """Export model to STEP format"""
        try:
            if BUILD123D_AVAILABLE and hasattr(model, "save_step"):
                model.save_step(filename)
                return True
            elif CADQUERY_AVAILABLE and hasattr(model, "val"):
                from OCP.STEPCAFControl import STEPCAFControl_Writer
                writer = STEPCAFControl_Writer()
                writer.Transfer_s(model.val, 2)  # STEPControl_AsIs
                writer.Write(filename)
                return True
        except Exception as e:
            logger.error(f"STEP export error: {e}")
            return False
    
    async def export_to_stl(self, model: Any, filename: str) -> bool:
        """Export model to STL format"""
        try:
            if BUILD123D_AVAILABLE and hasattr(model, "save_stl"):
                model.save_stl(filename)
                return True
            else:
                mesh_data = await self.generate_stl_preview(model)
                if mesh_data:
                    # Decode and write
                    stl_bytes = base64.b64decode(mesh_data)
                    with open(filename, "wb") as f:
                        f.write(stl_bytes)
                    return True
        except Exception as e:
            logger.error(f"STL export error: {e}")
            return False
