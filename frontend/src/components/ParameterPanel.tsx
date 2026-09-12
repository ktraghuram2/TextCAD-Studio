import React from 'react';
import { motion } from 'framer-motion';
import { Zap, AlertCircle, CheckCircle } from 'lucide-react';

interface ParameterPanelProps {
  parameters?: Record<string, any>;
  onParameterChange?: (key: string, value: any) => void;
  loading?: boolean;
}

const ParameterPanel: React.FC<ParameterPanelProps> = ({ 
  parameters = {}, 
  onParameterChange,
  loading = false 
}) => {
  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg shadow-2xl border border-slate-700 h-full flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-amber-600 to-orange-600 p-4 rounded-t-lg shadow-md">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Zap className="w-5 h-5" />
          Parameters
        </h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {Object.keys(parameters).length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-400">
            <AlertCircle className="w-8 h-8 mb-2" />
            <p>No parameters available</p>
            <p className="text-xs text-slate-500 mt-1">Generate a model to see parameters</p>
          </div>
        ) : (
          Object.entries(parameters).map(([key, value]) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-slate-700/50 border border-slate-600 rounded-lg p-3 hover:border-slate-500 transition-colors"
            >
              <label className="block text-sm font-semibold text-slate-200 mb-2 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              {typeof value === 'number' ? (
                <input
                  type="range"
                  min="0"
                  max="1000"
                  value={value}
                  onChange={(e) => onParameterChange?.(key, Number(e.target.value))}
                  disabled={loading}
                  className="w-full h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                />
              ) : typeof value === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => onParameterChange?.(key, e.target.checked)}
                  disabled={loading}
                  className="w-4 h-4 rounded"
                />
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => onParameterChange?.(key, e.target.value)}
                  disabled={loading}
                  className="w-full bg-slate-600 text-slate-100 px-2 py-1 rounded border border-slate-500 text-sm"
                />
              )}
              <span className="text-xs text-slate-400 mt-1 block">{value}</span>
            </motion.div>
          ))
        )}
      </div>

      {/* Info Footer */}
      <div className="border-t border-slate-700 bg-slate-800/50 p-4 rounded-b-lg">
        <div className="flex items-start gap-2 text-xs text-slate-400">
          <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-green-500" />
          <p>Adjust parameters and the model will update in real-time</p>
        </div>
      </div>
    </div>
  );
};

export default ParameterPanel;
