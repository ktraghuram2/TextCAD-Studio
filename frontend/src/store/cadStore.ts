import { create } from 'zustand';

export interface CADModel {
  id: string;
  name: string;
  prompt: string;
  code: string;
  preview?: string; // base64 STL or STL ASCII
  stl?: string;
  meshData?: any;
  info?: Record<string, any>;
  dimensions?: { width: number; height: number; depth: number };
  is2D?: boolean;
  timestamp?: Date;
}

export interface HistoryItem {
  id: string;
  prompt: string;
  code: string;
  timestamp: Date;
}

interface CADStore {
  // API Key & Universal Model Provider State
  apiKey: string;
  setApiKey: (key: string) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  provider: string; // 'auto' | 'gemini' | 'openai' | 'anthropic' | 'openrouter' | 'deepseek' | 'groq' | 'custom'
  setProvider: (provider: string) => void;
  customBaseUrl: string;
  setCustomBaseUrl: (url: string) => void;
  isApiKeyModalOpen: boolean;
  setIsApiKeyModalOpen: (open: boolean) => void;

  // Active Model State
  currentModel: CADModel | null;
  setCurrentModel: (model: CADModel | null) => void;
  designHistory: HistoryItem[];
  addToHistory: (item: HistoryItem) => void;
  clearHistory: () => void;

  // Viewer Controls State
  viewMode: '3d' | '2d';
  setViewMode: (mode: '3d' | '2d') => void;
  projectionView: 'top' | 'front' | 'side' | 'iso';
  setProjectionView: (view: 'top' | 'front' | 'side' | 'iso') => void;
  wireframe: boolean;
  setWireframe: (w: boolean) => void;
  showGrid: boolean;
  setShowGrid: (g: boolean) => void;
  showEdges: boolean;
  setShowEdges: (e: boolean) => void;

  // Execution & Generation Status
  isGenerating: boolean;
  setIsGenerating: (g: boolean) => void;
  generationStage: string;
  setGenerationStage: (stage: string) => void;
}

const LOCAL_STORAGE_KEY = 'textcad_api_key';
const LOCAL_STORAGE_MODEL = 'textcad_model_name';
const LOCAL_STORAGE_PROVIDER = 'textcad_ai_provider';
const LOCAL_STORAGE_BASE_URL = 'textcad_custom_base_url';

export const useCADStore = create<CADStore>((set) => ({
  apiKey: typeof window !== 'undefined' ? localStorage.getItem(LOCAL_STORAGE_KEY) || localStorage.getItem('textcad_gemini_api_key') || '' : '',
  setApiKey: (key: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_KEY, key);
    }
    set({ apiKey: key });
  },

  selectedModel: typeof window !== 'undefined' ? localStorage.getItem(LOCAL_STORAGE_MODEL) || 'gemini-2.0-flash' : 'gemini-2.0-flash',
  setSelectedModel: (model: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_MODEL, model);
    }
    set({ selectedModel: model });
  },

  provider: typeof window !== 'undefined' ? localStorage.getItem(LOCAL_STORAGE_PROVIDER) || 'auto' : 'auto',
  setProvider: (provider: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_PROVIDER, provider);
    }
    set({ provider });
  },

  customBaseUrl: typeof window !== 'undefined' ? localStorage.getItem(LOCAL_STORAGE_BASE_URL) || '' : '',
  setCustomBaseUrl: (url: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_BASE_URL, url);
    }
    set({ customBaseUrl: url });
  },

  isApiKeyModalOpen: false,
  setIsApiKeyModalOpen: (open: boolean) => set({ isApiKeyModalOpen: open }),

  currentModel: null,
  setCurrentModel: (model) => set({ currentModel: model }),

  designHistory: [],
  addToHistory: (item) =>
    set((state) => ({
      designHistory: [item, ...state.designHistory.slice(0, 19)],
    })),
  clearHistory: () => set({ designHistory: [] }),

  viewMode: '3d',
  setViewMode: (mode) => set({ viewMode: mode }),

  projectionView: 'iso',
  setProjectionView: (view) => set({ projectionView: view }),

  wireframe: false,
  setWireframe: (w) => set({ wireframe: w }),

  showGrid: true,
  setShowGrid: (g) => set({ showGrid: g }),

  showEdges: true,
  setShowEdges: (e) => set({ showEdges: e }),

  isGenerating: false,
  setIsGenerating: (g) => set({ isGenerating: g }),

  generationStage: 'idle',
  setGenerationStage: (stage) => set({ generationStage: stage }),
}));
