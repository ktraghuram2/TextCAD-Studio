import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Box,
  RotateCcw,
  Maximize2,
  Layers,
  Grid3X3,
  FileDown,
  Eye,
} from 'lucide-react';
import { useCADStore } from '../store/cadStore';
import { buildCadModel, parseSTL, exportToSTL, getModelDimensions } from '../services/cadCompiler';

const ModelViewer: React.FC = () => {
  const {
    currentModel,
    viewMode,
    setViewMode,
    projectionView,
    setProjectionView,
    wireframe,
    setWireframe,
    showGrid,
    setShowGrid,
    showEdges,
  } = useCADStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const orthoCameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelHolderRef = useRef<THREE.Group | null>(null);
  const gridHelperRef = useRef<THREE.GridHelper | null>(null);
  const primaryGeometryRef = useRef<THREE.BufferGeometry | null>(null);

  // Keep live ref of viewMode and projectionView to avoid stale closures in requestAnimationFrame
  const viewModeRef = useRef(viewMode);
  viewModeRef.current = viewMode;

  const [modelDims, setModelDims] = useState<{ width: number; height: number; depth: number } | null>(null);

  // Initialize Three.js scene
  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const width = containerRef.current.clientWidth || 600;
    const height = containerRef.current.clientHeight || 500;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0f1d); // Sleek dark slate CAD studio background
    sceneRef.current = scene;

    // 2. Perspective Camera (for 3D)
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 3000);
    camera.position.set(40, 35, 50);
    cameraRef.current = camera;

    // 3. Orthographic Camera (for 2D Technical view)
    const aspect = width / height;
    const frustumSize = 80;
    const orthoCamera = new THREE.OrthographicCamera(
      (frustumSize * aspect) / -2,
      (frustumSize * aspect) / 2,
      frustumSize / 2,
      frustumSize / -2,
      0.1,
      3000
    );
    orthoCamera.position.set(0, 100, 0);
    orthoCamera.lookAt(0, 0, 0);
    orthoCameraRef.current = orthoCamera;

    // 4. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;

    // 5. Controls
    const controls = new OrbitControls(camera, canvasRef.current);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    // 6. Professional CAD Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
    keyLight.position.set(80, 120, 90);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x60a5fa, 0.7);
    fillLight.position.set(-80, -40, -60);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xa78bfa, 0.6);
    rimLight.position.set(0, 80, -90);
    scene.add(rimLight);

    // 7. Ground Grid & Axes
    const grid = new THREE.GridHelper(100, 20, 0x3b82f6, 0x1e293b);
    grid.position.y = -0.01;
    scene.add(grid);
    gridHelperRef.current = grid;

    const axesHelper = new THREE.AxesHelper(25);
    axesHelper.position.set(0, 0.01, 0);
    scene.add(axesHelper);

    // 8. Model Container Group (Root centered at 0, 0, 0)
    const modelHolder = new THREE.Group();
    scene.add(modelHolder);
    modelHolderRef.current = modelHolder;

    // Render loop using live active camera
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const is2D = viewModeRef.current === '2d';
      const activeCamera = is2D ? orthoCameraRef.current! : cameraRef.current!;

      controls.update();
      renderer.render(scene, activeCamera);
    };
    animate();

    // Resize observer
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current) return;
      const newWidth = containerRef.current.clientWidth;
      const newHeight = containerRef.current.clientHeight;

      if (cameraRef.current) {
        cameraRef.current.aspect = newWidth / newHeight;
        cameraRef.current.updateProjectionMatrix();
      }

      if (orthoCameraRef.current) {
        const newAspect = newWidth / newHeight;
        orthoCameraRef.current.left = (frustumSize * newAspect) / -2;
        orthoCameraRef.current.right = (frustumSize * newAspect) / 2;
        orthoCameraRef.current.top = frustumSize / 2;
        orthoCameraRef.current.bottom = frustumSize / -2;
        orthoCameraRef.current.updateProjectionMatrix();
      }

      rendererRef.current.setSize(newWidth, newHeight);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
    };
  }, []);

  // Update Grid visibility
  useEffect(() => {
    if (gridHelperRef.current) {
      gridHelperRef.current.visible = showGrid;
    }
  }, [showGrid]);

  // Set Camera View Angle (Top, Front, Side, Iso)
  const setViewAngle = (view: 'top' | 'front' | 'side' | 'iso') => {
    setProjectionView(view);
    if (!controlsRef.current || !cameraRef.current || !orthoCameraRef.current) return;

    const dims = modelDims || { width: 20, height: 20, depth: 20 };
    const maxDim = Math.max(dims.width, dims.height, dims.depth, 15);
    const dist = maxDim * 2.5;

    // Update 3D perspective camera position
    switch (view) {
      case 'top':
        cameraRef.current.position.set(0, dist * 1.5, 0.001);
        cameraRef.current.up.set(0, 0, -1);
        break;
      case 'front':
        cameraRef.current.position.set(0, 0, dist * 1.5);
        cameraRef.current.up.set(0, 1, 0);
        break;
      case 'side':
        cameraRef.current.position.set(dist * 1.5, 0, 0);
        cameraRef.current.up.set(0, 1, 0);
        break;
      case 'iso':
      default:
        cameraRef.current.position.set(dist * 0.9, dist * 0.8, dist * 1.0);
        cameraRef.current.up.set(0, 1, 0);
        break;
    }

    cameraRef.current.lookAt(0, 0, 0);
    controlsRef.current.target.set(0, 0, 0);
    cameraRef.current.updateProjectionMatrix();
    controlsRef.current.update();

    // Also configure Orthographic camera for 2D Mode
    if (containerRef.current) {
      const aspect = containerRef.current.clientWidth / containerRef.current.clientHeight;
      const frustum = maxDim * 2.4;
      orthoCameraRef.current.left = (-frustum * aspect) / 2;
      orthoCameraRef.current.right = (frustum * aspect) / 2;
      orthoCameraRef.current.top = frustum / 2;
      orthoCameraRef.current.bottom = -frustum / 2;

      switch (view) {
        case 'top':
          orthoCameraRef.current.position.set(0, 100, 0.001);
          orthoCameraRef.current.up.set(0, 0, -1);
          break;
        case 'front':
          orthoCameraRef.current.position.set(0, 0, 100);
          orthoCameraRef.current.up.set(0, 1, 0);
          break;
        case 'side':
          orthoCameraRef.current.position.set(100, 0, 0);
          orthoCameraRef.current.up.set(0, 1, 0);
          break;
        case 'iso':
        default:
          orthoCameraRef.current.position.set(70, 70, 70);
          orthoCameraRef.current.up.set(0, 1, 0);
          break;
      }

      orthoCameraRef.current.lookAt(0, 0, 0);
      orthoCameraRef.current.updateProjectionMatrix();
    }
  };

  // Switch between 3D and 2D view
  useEffect(() => {
    if (!controlsRef.current || !cameraRef.current || !orthoCameraRef.current) return;

    if (viewMode === '2d') {
      setViewAngle('top');
      controlsRef.current.object = orthoCameraRef.current;
    } else {
      controlsRef.current.object = cameraRef.current;
      setViewAngle('iso');
    }
  }, [viewMode]);

  // Load and assemble the CAD model
  useEffect(() => {
    if (!modelHolderRef.current || !sceneRef.current) return;

    // Clear previous model objects
    while (modelHolderRef.current.children.length > 0) {
      const child = modelHolderRef.current.children[0];
      modelHolderRef.current.remove(child);
    }

    if (!currentModel) {
      setModelDims(null);
      return;
    }

    try {
      let cadResult;

      if (currentModel.stl && currentModel.stl.length > 50) {
        const geom = parseSTL(currentModel.stl);
        const mat = new THREE.MeshStandardMaterial({
          color: viewMode === '2d' ? 0x38bdf8 : 0x2563eb,
          roughness: 0.35,
          metalness: 0.45,
          wireframe,
        });
        const mesh = new THREE.Mesh(geom, mat);
        const grp = new THREE.Group();
        grp.add(mesh);
        cadResult = {
          group: grp,
          primaryGeometry: geom,
          dimensions: getModelDimensions(geom),
        };
      } else {
        // Build using our intelligent solid and 2D drafting CAD compiler
        cadResult = buildCadModel(
          currentModel.meshData?.features || [],
          currentModel.code || '',
          viewMode,
          wireframe,
          showEdges,
          currentModel.is2D,
          currentModel.prompt
        );
      }

      primaryGeometryRef.current = cadResult.primaryGeometry;
      setModelDims(cadResult.dimensions);

      // Add the centered model to the viewport
      modelHolderRef.current.add(cadResult.group);

      // Frame camera to the model
      const maxDim = Math.max(cadResult.dimensions.width, cadResult.dimensions.height, cadResult.dimensions.depth, 10);
      const camDist = maxDim * 2.8;

      if (viewMode === '2d' || cadResult.is2D) {
        if (orthoCameraRef.current && containerRef.current) {
          const aspect = containerRef.current.clientWidth / containerRef.current.clientHeight;
          const frustum = maxDim * 1.8;
          orthoCameraRef.current.left = (-frustum * aspect) / 2;
          orthoCameraRef.current.right = (frustum * aspect) / 2;
          orthoCameraRef.current.top = frustum / 2;
          orthoCameraRef.current.bottom = -frustum / 2;
          orthoCameraRef.current.position.set(0, 100, 0.001);
          orthoCameraRef.current.up.set(0, 0, -1);
          orthoCameraRef.current.lookAt(0, 0, 0);
          orthoCameraRef.current.updateProjectionMatrix();
        }
        if (controlsRef.current && orthoCameraRef.current) {
          controlsRef.current.object = orthoCameraRef.current;
          controlsRef.current.target.set(0, 0, 0);
          controlsRef.current.update();
        }
      } else {
        if (cameraRef.current && controlsRef.current) {
          controlsRef.current.object = cameraRef.current;
          cameraRef.current.position.set(camDist * 0.9, camDist * 0.8, camDist * 1.0);
          cameraRef.current.lookAt(0, 0, 0);
          controlsRef.current.target.set(0, 0, 0);
          cameraRef.current.updateProjectionMatrix();
          controlsRef.current.update();
        }
      }
    } catch (err) {
      console.error('Failed to construct CAD model:', err);
    }
  }, [currentModel, wireframe, showEdges, viewMode]);

  // Export STL
  const handleExportSTL = () => {
    const geom = primaryGeometryRef.current;
    if (!geom) return;

    const stlContent = exportToSTL(geom, currentModel?.name || 'TextCAD_Model');
    const blob = new Blob([stlContent], { type: 'model/stl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(currentModel?.name || 'model').toLowerCase().replace(/\s+/g, '_')}.stl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleResetView = () => {
    setViewAngle(viewMode === '2d' ? 'top' : 'iso');
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full bg-slate-900/90 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-700/70 overflow-hidden relative group select-none"
    >
      {/* Top Toolbar */}
      <div className="bg-gradient-to-r from-slate-850 via-slate-800 to-slate-850 px-4 py-3 border-b border-slate-700/80 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
            <Box className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              {currentModel?.is2D || viewMode === '2d' ? '2D Technical Drawing' : '3D Model Viewer'}
              {currentModel && (
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                  currentModel.is2D || viewMode === '2d'
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                }`}>
                  {currentModel.is2D || viewMode === '2d' ? '📐 2D CAD Sketch' : '3D Solid Part'}
                </span>
              )}
            </h2>
            <p className="text-[11px] text-slate-400 truncate max-w-[200px]">
              {currentModel?.name || 'Interactive CAD Viewport'}
            </p>
          </div>
        </div>

        {/* View Mode & View Controls */}
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {/* 3D vs 2D Mode Switch */}
          <div className="bg-slate-900/80 p-1 rounded-xl border border-slate-700/80 flex items-center gap-1">
            <button
              onClick={() => setViewMode('3d')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                viewMode === '3d'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              3D View
            </button>
            <button
              onClick={() => setViewMode('2d')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                viewMode === '2d'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              2D View
            </button>
          </div>

          {/* View Angle Presets (Top, Front, Side, Iso) */}
          <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-700/80 items-center gap-1">
            {(['top', 'front', 'side', 'iso'] as const).map((view) => (
              <button
                key={view}
                onClick={() => setViewAngle(view)}
                className={`px-2 py-0.5 text-[11px] font-semibold uppercase rounded-md transition-colors ${
                  projectionView === view
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title={`Switch to ${view.toUpperCase()} view`}
              >
                {view}
              </button>
            ))}
          </div>

          {/* Center & Reset View Button */}
          <button
            onClick={handleResetView}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Center & Reset View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Wireframe Toggle */}
          <button
            onClick={() => setWireframe(!wireframe)}
            className={`p-1.5 rounded-lg transition-colors ${
              wireframe ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            title="Toggle Wireframe"
          >
            <Layers className="w-4 h-4" />
          </button>

          {/* Grid Toggle */}
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg transition-colors ${
              showGrid ? 'text-blue-400 bg-slate-800' : 'text-slate-500 hover:text-slate-300'
            }`}
            title="Toggle Grid"
          >
            <Grid3X3 className="w-4 h-4" />
          </button>

          {/* Export STL */}
          {currentModel && (
            <button
              onClick={handleExportSTL}
              className="px-2.5 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
              title="Download STL File"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>STL</span>
            </button>
          )}

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            title="Toggle Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 3D / 2D Canvas Area */}
      <div className="flex-1 relative bg-slate-950/60 overflow-hidden cursor-grab active:cursor-grabbing">
        <canvas ref={canvasRef} className="w-full h-full block" />

        {/* Empty State */}
        {!currentModel && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none p-6 text-center">
            <div className="p-4 bg-slate-850/80 border border-slate-700/80 rounded-2xl shadow-xl mb-4 text-blue-400 backdrop-blur-sm">
              <Box className="w-10 h-10 animate-pulse" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">3D / 2D Viewport Ready</h3>
            <p className="text-xs text-slate-400 max-w-sm">
              Enter a prompt in the chat window. Your model will automatically compile and render in the exact middle of this viewport.
            </p>
          </div>
        )}

        {/* 2D Blueprint Overlay Watermark (when in 2D Mode) */}
        {viewMode === '2d' && (
          <div className="absolute top-3 right-3 pointer-events-none px-3 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-xl text-[11px] text-blue-300 font-mono backdrop-blur-md">
            📐 2D BLUEPRINT VIEW: {projectionView.toUpperCase()} ORTHOGRAPHIC
          </div>
        )}

        {/* Overlay Badges (Dimensions, Coordinates, View Orientation) */}
        {currentModel && (
          <div className="absolute bottom-3 left-3 pointer-events-none flex flex-col gap-1.5 z-10">
            {modelDims && (
              <div className="px-3 py-1.5 bg-slate-900/90 border border-slate-700/80 rounded-xl text-[11px] text-slate-300 shadow-lg backdrop-blur-md flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${currentModel?.is2D || viewMode === '2d' ? 'bg-cyan-400' : 'bg-blue-500'}`}></span>
                <span>
                  {currentModel?.is2D || modelDims.depth === 0 ? (
                    <>
                      2D Sheet Size: <strong>{modelDims.width}</strong> × <strong>{modelDims.height}</strong> mm (Planar Sketch)
                    </>
                  ) : (
                    <>
                      Size: <strong>{modelDims.width}</strong> × <strong>{modelDims.height}</strong> ×{' '}
                      <strong>{modelDims.depth}</strong> mm
                    </>
                  )}
                </span>
              </div>
            )}
            <div className="px-3 py-1 bg-slate-900/80 border border-slate-800 rounded-lg text-[10px] text-slate-400 backdrop-blur-sm">
              {currentModel?.is2D || viewMode === '2d'
                ? '2D Mode • Left Drag / Scroll: Pan & Zoom CAD Drawing'
                : 'Center: (0.0, 0.0, 0.0) • Left Drag: Rotate • Right Drag: Pan • Scroll: Zoom'}
            </div>
          </div>
        )}
      </div>

      {/* Viewport Footer Bar */}
      <div className="p-2.5 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            WebGL 2.0 CAD Studio
          </span>
          <span className="text-blue-400 font-mono text-[10px]">
            Mode: {viewMode.toUpperCase()} ({projectionView.toUpperCase()})
          </span>
        </div>
        <div className="text-[10px] text-slate-500">
          Auto-Centered • True Scale (mm)
        </div>
      </div>
    </div>
  );
};

export default ModelViewer;
