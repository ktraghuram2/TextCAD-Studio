import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, MessageSquare, Key, Sparkles, Trash2, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCADStore } from '../store/cadStore';
import { generateCadWithAI } from '../services/aiProvider';
import { exportToSTL } from '../services/cadCompiler';
import { apiClient } from '../services/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  modelName?: string;
  cadCode?: string;
  dimensions?: { width: number; height: number; depth: number };
  timestamp: Date;
}

const QUICK_PROMPTS = [
  '10mm Cube with 4mm hole',
  'Flanged Pipe Coupling 50mm',
  'NEMA 17 Stepper Mount',
  'Hexagonal Bolt M10 × 40mm',
];

const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    apiKey,
    selectedModel,
    provider,
    customBaseUrl,
    setIsApiKeyModalOpen,
    currentModel,
    setCurrentModel,
    designHistory,
    addToHistory,
    isGenerating,
    setIsGenerating,
    generationStage,
    setGenerationStage,
  } = useCADStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSendMessage = async (textToSend?: string) => {
    const promptText = (textToSend || input).trim();
    if (!promptText || isGenerating) return;

    // Check if API key is present (or custom endpoint)
    if (!apiKey && provider !== 'custom') {
      setIsApiKeyModalOpen(true);
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: promptText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsGenerating(true);
    setGenerationStage(`Prompting ${selectedModel || 'AI'}...`);

    try {
      // 1. Generate CAD specification using AI with user's key and model
      setGenerationStage('Generating CadQuery / Build123d code...');
      const modelSpec = await generateCadWithAI(
        promptText,
        apiKey,
        selectedModel,
        provider,
        customBaseUrl,
        designHistory.map((h) => ({ prompt: h.prompt, code: h.code }))
      );

      setGenerationStage('Compiling 3D & 2D geometry...');

      // 2. Try backend execution if available, otherwise use direct browser composite geometry
      let stlString = '';
      try {
        const backendRes = await apiClient.post('/api/chat/generate', {
          message: promptText,
          api_key: apiKey,
          cad_code: modelSpec.cadCode,
        });
        if (backendRes.data?.model_preview) {
          stlString = backendRes.data.model_preview;
        }
      } catch {
        // Backend not running or optional - proceed seamlessly with browser CAD compiler
      }

      // 3. Update CAD Store (updates both 3D/2D Viewer and Code Viewer)
      const newCADModel = {
        id: Date.now().toString(),
        name: modelSpec.name,
        prompt: promptText,
        code: modelSpec.cadCode,
        preview: stlString || undefined,
        stl: stlString || undefined,
        meshData: { features: modelSpec.features },
        dimensions: modelSpec.dimensions,
        is2D: modelSpec.is2D,
        timestamp: new Date(),
      };

      if (modelSpec.is2D) {
        useCADStore.getState().setViewMode('2d');
        useCADStore.getState().setProjectionView('top');
      }

      setCurrentModel(newCADModel);
      addToHistory({
        id: newCADModel.id,
        prompt: promptText,
        code: modelSpec.cadCode,
        timestamp: new Date(),
      });

      // 4. Add Assistant response message
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: modelSpec.description || (modelSpec.is2D ? `Successfully generated 2D CAD technical drawing for "${modelSpec.name}".` : `Successfully generated 3D CAD model for "${modelSpec.name}".`),
        modelName: modelSpec.name,
        cadCode: modelSpec.cadCode,
        dimensions: modelSpec.dimensions,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('CAD Generation Error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to generate CAD model. Please verify your API key.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsGenerating(false);
      setGenerationStage('idle');
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/90 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-700/70 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-850 via-slate-800 to-slate-850 px-4 py-3 border-b border-slate-700/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              CAD Design Chat
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Natural Language
              </span>
            </h2>
            <p className="text-[11px] text-slate-400">Text-to-3D Prompt Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              title="Clear Conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          {!apiKey && (
            <button
              onClick={() => setIsApiKeyModalOpen(true)}
              className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors animate-pulse"
            >
              <Key className="w-3 h-3" />
              <span>Set Key</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/40">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full p-4 text-center">
            <div className="p-4 bg-gradient-to-tr from-blue-600/20 to-purple-600/20 border border-blue-500/20 rounded-2xl mb-3 text-blue-400 shadow-inner">
              <Sparkles className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">Design in Plain English</h3>
            <p className="text-xs text-slate-400 max-w-xs mb-5">
              Describe your mechanical part or 3D object. TextCAD will write the Python CAD code and render the 3D model in the center.
            </p>

            {/* Quick Prompt Chips */}
            <div className="w-full max-w-xs space-y-1.5">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-left">
                Suggested Prompts
              </p>
              <div className="grid grid-cols-1 gap-1.5">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSendMessage(prompt)}
                    className="w-full text-left px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-300 hover:text-white transition-all hover:border-blue-500/50 flex items-center justify-between group"
                  >
                    <span>{prompt}</span>
                    <span className="text-slate-600 group-hover:text-blue-400 transition-colors">→</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[88%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-none shadow-md shadow-blue-500/10'
                  : 'bg-slate-850 border border-slate-700/80 text-slate-200 rounded-bl-none shadow-md'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-1.5 font-semibold text-[11px] text-blue-400 mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{msg.modelName || 'TextCAD Studio'}</span>
                </div>
              )}
              <p>{msg.content}</p>

              {msg.dimensions && (
                <div className="mt-2 pt-2 border-t border-slate-700/60 flex items-center gap-2 text-[10px] text-slate-400">
                  <span>Size:</span>
                  <span className="font-mono text-slate-300">
                    {msg.dimensions.width} × {msg.dimensions.height} × {msg.dimensions.depth} mm
                  </span>
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-500 mt-1 px-1">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        ))}

        {isGenerating && (
          <div className="flex items-center gap-2 text-xs text-blue-400 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl w-fit animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{generationStage}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 bg-slate-900 border-t border-slate-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            placeholder={
              apiKey || provider === 'custom'
                ? `Describe your 3D CAD design (using ${selectedModel || 'AI'})...`
                : 'Click "Set Key" above to configure your API key & model...'
            }
            disabled={isGenerating}
            className="flex-1 bg-slate-800 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={isGenerating || !input.trim()}
            className="px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-500/20 transition-all flex items-center gap-1.5"
          >
            {isGenerating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span className="hidden sm:inline">Generate</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
