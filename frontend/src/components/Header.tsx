import React from 'react';
import { Key, Box, Sparkles, CheckCircle2, AlertTriangle, ExternalLink } from 'lucide-react';
import { useCADStore } from '../store/cadStore';

const Header: React.FC = () => {
  const { apiKey, selectedModel, setIsApiKeyModalOpen, currentModel } = useCADStore();

  return (
    <header className="border-b border-slate-700/80 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-40">
      <div className="w-full px-6 py-3.5 flex items-center justify-between">
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Box className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
                TextCAD Studio
              </h1>
              <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                v2.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Prompt-to-CAD • 3D/2D Viewport & Code Engine
            </p>
          </div>
        </div>

        {/* Center: Current Model Info if available */}
        {currentModel && (
          <div className="hidden md:flex items-center gap-3 px-4 py-1.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
            <span className="text-slate-400 font-medium">Active:</span>
            <span className="font-semibold text-white">{currentModel.name}</span>
            {currentModel.dimensions && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-blue-300 font-mono text-[11px]">
                  {currentModel.dimensions.width}×{currentModel.dimensions.height}×{currentModel.dimensions.depth}mm
                </span>
              </>
            )}
          </div>
        )}

        {/* Right Controls: API Key & External links */}
        <div className="flex items-center gap-3">
          {/* API Key Status / Config Trigger Button */}
          <button
            onClick={() => setIsApiKeyModalOpen(true)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all border ${
              apiKey
                ? 'bg-slate-800/80 hover:bg-slate-800 text-slate-200 border-slate-700 hover:border-blue-500/50'
                : 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border-amber-500/40 hover:border-amber-400 shadow-md shadow-amber-500/10 animate-pulse'
            }`}
          >
            <Key className="w-3.5 h-3.5 text-amber-400" />
            <span>
              {apiKey ? (selectedModel ? `${selectedModel}` : 'AI Configured') : 'Set API Key / Model'}
            </span>
            {apiKey ? (
              <span className="w-2 h-2 rounded-full bg-emerald-500" title="API Key verified"></span>
            ) : (
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
            )}
          </button>

          <a
            href="https://github.com/ktraghuram2/TextCAD-Studio"
            target="_blank"
            rel="noreferrer"
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors text-xs flex items-center gap-1.5"
            title="GitHub Repository"
          >
            <span className="hidden sm:inline">GitHub</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </header>
  );
};

export default Header;
