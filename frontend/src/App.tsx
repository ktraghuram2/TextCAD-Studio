import React from 'react';
import ChatWindow from './components/ChatWindow';
import ModelViewer from './components/ModelViewer';
import ParameterPanel from './components/ParameterPanel';
import { useCADStore } from './store/cadStore';
import { motion } from 'framer-motion';

const App: React.FC = () => {
  const { currentModel } = useCADStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <div className="text-3xl">🎨</div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                TextCAD Studio
              </h1>
              <p className="text-xs text-slate-400">AI-powered 3D CAD Design</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 text-sm text-slate-400"
          >
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
            API Connected
          </motion.div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-screen">
          {/* Chat Window - Left Side */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="lg:col-span-1 min-h-96"
          >
            <ChatWindow />
          </motion.div>

          {/* 3D Viewer - Center */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="lg:col-span-1 min-h-96"
          >
            <ModelViewer modelData={currentModel?.preview} />
          </motion.div>

          {/* Parameters - Right Side */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="lg:col-span-1 min-h-96"
          >
            <ParameterPanel parameters={currentModel?.info} />
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-700 bg-slate-900/50 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-6 text-center text-sm text-slate-400">
          <p>TextCAD Studio © 2024 | Powered by Gemini API, CadQuery & Build123d</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
