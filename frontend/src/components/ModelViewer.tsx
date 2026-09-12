import React, { useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';
import { Download, RotateCcw, ZoomIn } from 'lucide-react';

interface ModelViewerProps {
  modelData?: string; // Base64 encoded STL
  onExport?: (format: 'stl' | 'step') => void;
}

const ModelViewer: React.FC<ModelViewerProps> = ({ modelData, onExport }) => {
  const meshRef = useRef<THREE.Mesh>(null);

  const parseSTL = (data: string): THREE.BufferGeometry => {
    // Decode base64 STL data
    const binaryString = atob(data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Parse STL (simplified - use trimesh library for production)
    const geometry = new THREE.BufferGeometry();
    
    // Placeholder: Create a default box for demo
    const boxGeometry = new THREE.BoxGeometry(10, 10, 10);
    geometry.copy(boxGeometry);

    return geometry;
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg shadow-2xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-4 shadow-md">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6z" />
          </svg>
          3D Model Viewer
        </h2>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 bg-slate-800 relative">
        {modelData ? (
          <Canvas
            camera={{ position: [0, 0, 50], fov: 75 }}
            style={{ width: '100%', height: '100%' }}
          >
            <ambientLight intensity={0.8} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <mesh ref={meshRef} geometry={parseSTL(modelData)}>
              <meshPhongMaterial color="#3b82f6" />
            </mesh>
            <Grid args={[100, 100]} />
            <OrbitControls />
          </Canvas>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <div className="text-5xl mb-4">📦</div>
            <p className="text-lg">No model loaded</p>
            <p className="text-sm text-slate-500 mt-2">Generate a design to see preview</p>
          </div>
        )}
      </div>

      {/* Footer Controls */}
      {modelData && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-slate-800 border-t border-slate-700 p-4 flex gap-2 justify-end"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset View
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onExport?.('stl')}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors font-semibold"
          >
            <Download className="w-4 h-4" />
            Export STL
          </motion.button>
        </motion.div>
      )}
    </div>
  );
};

export default ModelViewer;
