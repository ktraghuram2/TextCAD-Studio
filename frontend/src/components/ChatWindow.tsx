import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader, Download, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import { useCADStore } from '../store/cadStore';
import { apiClient } from '../services/api';
import MessageBubble from './MessageBubble';
import CodeBlock from './CodeBlock';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cadCode?: string;
  modelPreview?: string;
  timestamp: Date;
}

const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { currentModel, setCurrentModel, designHistory, addToHistory } = useCADStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Call API to generate CAD
      const response = await apiClient.post('/chat/generate', {
        message: input,
        design_history: designHistory.slice(-5), // Last 5 designs
        model_context: currentModel?.info,
      });

      // Add assistant message with CAD code and preview
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.data.message,
        cadCode: response.data.cad_code,
        modelPreview: response.data.model_preview,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentModel({
        id: response.data.design_id,
        preview: response.data.model_preview,
        code: response.data.cad_code,
        info: { timestamp: new Date() },
      });
      addToHistory(response.data.cad_code);
    } catch (error) {
      console.error('Failed to generate CAD:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to generate CAD model'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg shadow-2xl border border-slate-700">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 rounded-t-lg shadow-md">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
            </svg>
            TextCAD Chat
          </h2>
          <span className="text-sm text-blue-100">{messages.length} messages</span>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-800/50">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-6xl mb-4">🎨</div>
            <h3 className="text-xl font-bold text-white mb-2">Welcome to TextCAD Studio</h3>
            <p className="text-slate-400 max-w-sm">
              Describe your 3D model design in natural language and watch it come to life!
            </p>
            <div className="mt-6 space-y-2 text-left">
              <p className="text-sm text-slate-300 font-semibold">Try examples like:</p>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• "Create a 10mm cube"</li>
                <li>• "Design a cylindrical container with 50mm diameter"</li>
                <li>• "Make a hexagonal bolt 20mm wide"</li>
              </ul>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <MessageBubble
              message={message}
              isUser={message.role === 'user'}
              cadCode={message.cadCode}
            />
          </motion.div>
        ))}

        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-slate-400"
          >
            <Loader className="w-4 h-4 animate-spin" />
            <span>Generating CAD model...</span>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-700 bg-slate-800 p-4 rounded-b-lg">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Describe your CAD design..."
            className="flex-1 bg-slate-700 text-white px-4 py-3 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 placeholder-slate-400"
            disabled={loading}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg font-semibold hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            Send
          </motion.button>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
