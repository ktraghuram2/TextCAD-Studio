import React from 'react';
import { motion } from 'framer-motion';
import CodeBlock from './CodeBlock';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cadCode?: string;
  modelPreview?: string;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: Message;
  isUser: boolean;
  cadCode?: string;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isUser, cadCode }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-md lg:max-w-lg xl:max-w-xl rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-br-none'
            : 'bg-slate-700 text-slate-100 rounded-bl-none'
        }`}
      >
        <p className="text-sm leading-relaxed">{message.content}</p>
        
        {cadCode && (
          <div className="mt-3">
            <CodeBlock code={cadCode} language="python" />
          </div>
        )}

        <span className="text-xs opacity-70 mt-2 block">
          {message.timestamp.toLocaleTimeString()}
        </span>
      </div>
    </motion.div>
  );
};

export default MessageBubble;
