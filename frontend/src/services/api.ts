import axios from 'axios';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const generateCAD = async (prompt: string, context?: Record<string, any>) => {
  return apiClient.post('/api/chat/generate', {
    message: prompt,
    model_context: context,
  });
};

export const generateFromCode = async (code: string) => {
  return apiClient.post('/api/cad/generate-from-code', {
    code,
  });
};

export const exportModel = async (modelId: string, format: 'stl' | 'step') => {
  return apiClient.post(`/api/export/${format}`, {
    model_id: modelId,
  }, {
    responseType: 'blob',
  });
};
