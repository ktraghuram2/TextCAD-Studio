import React, { useState } from 'react';
import { Key, Check, AlertCircle, ExternalLink, X, Eye, EyeOff, Loader, Cpu, Globe, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCADStore } from '../store/cadStore';
import { testAIConnection } from '../services/aiProvider';

const POPULAR_MODELS = [
  'gemini-2.0-flash',
  'gpt-4o',
  'claude-3-5-sonnet-20241022',
  'deepseek-chat',
  'llama-3.3-70b-versatile',
];

const ApiKeyModal: React.FC = () => {
  const {
    apiKey,
    setApiKey,
    selectedModel,
    setSelectedModel,
    provider,
    setProvider,
    customBaseUrl,
    setCustomBaseUrl,
    isApiKeyModalOpen,
    setIsApiKeyModalOpen,
  } = useCADStore();

  const [inputKey, setInputKey] = useState(apiKey);
  const [inputModel, setInputModel] = useState(selectedModel || '');
  const [selectedProvider, setSelectedProvider] = useState(provider || 'auto');
  const [inputBaseUrl, setInputBaseUrl] = useState(customBaseUrl || '');
  const [showKey, setShowKey] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(!!customBaseUrl);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ status: 'idle' | 'success' | 'error'; message?: string }>({ status: 'idle' });

  if (!isApiKeyModalOpen) return null;

  const handleSave = () => {
    setApiKey(inputKey.trim());
    setSelectedModel(inputModel.trim());
    setProvider(selectedProvider);
    setCustomBaseUrl(inputBaseUrl.trim());
    setIsApiKeyModalOpen(false);
  };

  const handleTest = async () => {
    if (!inputKey.trim() && selectedProvider !== 'custom') {
      setTestResult({ status: 'error', message: 'Please enter an API key to test' });
      return;
    }
    setTesting(true);
    setTestResult({ status: 'idle' });

    const res = await testAIConnection(
      inputKey.trim(),
      inputModel.trim(),
      selectedProvider,
      inputBaseUrl.trim()
    );

    setTesting(false);
    if (res.valid) {
      setTestResult({
        status: 'success',
        message: `Connection successful! Verified with ${res.detected || 'AI Provider'}.`,
      });
    } else {
      setTestResult({ status: 'error', message: res.error || 'Connection failed' });
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden text-slate-100"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/10 rounded-xl backdrop-blur-md">
                <Key className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">AI Provider & API Key Setup</h3>
                <p className="text-xs text-blue-100">Compatible with Gemini, OpenAI, Claude, DeepSeek, Groq & Custom</p>
              </div>
            </div>
            <button
              onClick={() => setIsApiKeyModalOpen(false)}
              className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
            {/* 1. API Key Input */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                API Key
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={inputKey}
                  onChange={(e) => {
                    setInputKey(e.target.value);
                    setTestResult({ status: 'idle' });
                  }}
                  placeholder="Paste your API key (AIzaSy..., sk-..., gsk_..., etc.)"
                  className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 pr-10 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-200"
                  title={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Stored privately in your browser local storage. Never sent to any external server.
              </p>
            </div>

            {/* 2. Custom Model Name Input (Blank/Free-form as requested) */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-blue-400" />
                  Model Name
                </label>
                <span className="text-[11px] text-slate-500">Type any model name</span>
              </div>
              <input
                type="text"
                value={inputModel}
                onChange={(e) => {
                  setInputModel(e.target.value);
                  setTestResult({ status: 'idle' });
                }}
                placeholder="Enter model (e.g., gemini-2.0-flash, gpt-4o, claude-3-5-sonnet, deepseek-chat)"
                className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono"
              />
              {/* Quick Model Suggestions */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                <span className="text-[10px] text-slate-500 self-center">Quick fill:</span>
                {POPULAR_MODELS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => {
                      setInputModel(m);
                      setTestResult({ status: 'idle' });
                    }}
                    className={`px-2 py-0.5 rounded-md text-[10px] font-mono transition-colors border ${
                      inputModel === m
                        ? 'bg-blue-600 text-white border-blue-500'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200 hover:bg-slate-750'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* 3. AI Provider Selection */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Provider Protocol
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
                {[
                  { id: 'auto', label: '⚡ Auto-Detect' },
                  { id: 'gemini', label: 'Google Gemini' },
                  { id: 'openai', label: 'OpenAI' },
                  { id: 'anthropic', label: 'Claude' },
                  { id: 'deepseek', label: 'DeepSeek' },
                  { id: 'openrouter', label: 'OpenRouter' },
                  { id: 'groq', label: 'Groq' },
                  { id: 'custom', label: 'Custom / Local' },
                ].map((prov) => (
                  <button
                    key={prov.id}
                    type="button"
                    onClick={() => {
                      setSelectedProvider(prov.id);
                      if (prov.id === 'custom') setShowAdvanced(true);
                      setTestResult({ status: 'idle' });
                    }}
                    className={`px-2.5 py-1.5 rounded-xl text-[11px] font-medium transition-all text-center border ${
                      selectedProvider === prov.id
                        ? 'bg-gradient-to-r from-blue-600/30 to-indigo-600/30 border-blue-500 text-white shadow-sm'
                        : 'bg-slate-800/60 border-slate-700/70 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                  >
                    {prov.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 4. Optional Custom Base URL (Ollama, LMStudio, vLLM, Proxies) */}
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-[11px] text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
              >
                <Globe className="w-3 h-3" />
                <span>{showAdvanced ? 'Hide Custom Base URL' : 'Configure Custom Endpoint / Base URL (Ollama, LocalAI...)'}</span>
              </button>

              {showAdvanced && (
                <div className="mt-2 p-3 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-1.5">
                  <label className="block text-[11px] font-medium text-slate-400">
                    API Base URL (OpenAI-compatible)
                  </label>
                  <input
                    type="text"
                    value={inputBaseUrl}
                    onChange={(e) => setInputBaseUrl(e.target.value)}
                    placeholder="e.g. http://localhost:11434/v1 or https://api.deepseek.com/v1"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="text-[10px] text-slate-500">
                    Leave blank to use official cloud endpoints. For local Ollama use: http://localhost:11434/v1
                  </p>
                </div>
              )}
            </div>

            {/* Test Status Banner */}
            {testResult.status === 'success' && (
              <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs">
                <Check className="w-4 h-4 flex-shrink-0" />
                <span>{testResult.message}</span>
              </div>
            )}
            {testResult.status === 'error' && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{testResult.message}</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 bg-slate-950/70 border-t border-slate-800 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleTest}
              disabled={testing || (!inputKey.trim() && selectedProvider !== 'custom')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-300 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 border border-slate-700"
            >
              {testing ? <Loader className="w-3.5 h-3.5 animate-spin" /> : null}
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsApiKeyModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/25 transition-all"
              >
                Save Settings
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ApiKeyModal;
