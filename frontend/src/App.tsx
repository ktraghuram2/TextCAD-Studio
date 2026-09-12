import React from 'react';
import Header from './components/Header';
import ChatWindow from './components/ChatWindow';
import ModelViewer from './components/ModelViewer';
import CodeViewer from './components/CodeViewer';
import ApiKeyModal from './components/ApiKeyModal';

const App: React.FC = () => {
  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden select-none">
      {/* Top Navigation & Status Bar */}
      <Header />

      {/* Main Studio Workspace: 3 Windows Layout */}
      {/* 1. Chat Window (Left) | 2. 3D/2D Model Viewer (Middle) | 3. Code Viewer (Right) */}
      <main className="flex-1 p-3 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-full">
          {/* Window 1: Chat Window (Left) */}
          <section className="lg:col-span-3 h-full min-h-[300px]">
            <ChatWindow />
          </section>

          {/* Window 2: 3D / 2D Model Viewer Window (Middle - Centered & Prominent) */}
          <section className="lg:col-span-6 h-full min-h-[400px]">
            <ModelViewer />
          </section>

          {/* Window 3: Code Viewer Window (Right) */}
          <section className="lg:col-span-3 h-full min-h-[300px]">
            <CodeViewer />
          </section>
        </div>
      </main>

      {/* API Key Modal for pasting Gemini API Key */}
      <ApiKeyModal />
    </div>
  );
};

export default App;
