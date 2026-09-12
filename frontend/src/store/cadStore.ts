import { create } from 'zustand';

interface CADModel {
  id: string;
  preview?: string;
  code: string;
  info: Record<string, any>;
}

interface CADStore {
  currentModel: CADModel | null;
  setCurrentModel: (model: CADModel | null) => void;
  designHistory: string[];
  addToHistory: (code: string) => void;
  clearHistory: () => void;
}

export const useCADStore = create<CADStore>((set) => ({
  currentModel: null,
  setCurrentModel: (model) => set({ currentModel: model }),
  designHistory: [],
  addToHistory: (code) =>
    set((state) => ({
      designHistory: [...state.designHistory, code],
    })),
  clearHistory: () => set({ designHistory: [] }),
}));
