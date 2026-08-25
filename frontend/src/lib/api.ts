import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (data: { username: string; email?: string; password: string }) =>
    api.post('/auth/register', data),
};

export const solveApi = {
  solve: (request: any) => api.post('/solve', request),
};

export const networkApi = {
  list: (params?: { limit?: number; offset?: number }) => api.get('/networks', { params }),
  get: (id: string) => api.get(`/networks/${id}`),
  create: (data: any) => api.post('/networks', data),
  delete: (id: string) => api.delete(`/networks/${id}`),
};

export const mlApi = {
  listModels: () => api.get('/models'),
  predict: (request: any) => api.post('/predict', request),
};

export default api;