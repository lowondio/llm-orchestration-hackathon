import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const checkHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export const deployAgent = async (graph: { nodes: any[]; edges: any[]; graph_id?: string }) => {
  const response = await api.post('/api/deploy', graph);
  return response.data;
};

export const runGraph = async (graphId: string, input: string = "Hello, world!") => {
  const response = await api.post(`/api/run/${graphId}`, { input });
  return response.data;
};

export const saveGraph = async (graph: { id?: string; name: string; description: string; config: any }) => {
  const response = await api.post('/api/graphs', graph);
  return response.data;
};

export const updateGraph = async (graphId: string, graph: { name: string; description: string; config: any }) => {
  const response = await api.put(`/api/graphs/${graphId}`, graph);
  return response.data;
};

export const listGraphs = async () => {
  const response = await api.get('/api/graphs');
  return response.data;
};

export const loadGraph = async (graphId: string) => {
  const response = await api.get(`/api/graphs/${graphId}`);
  return response.data;
};

export const deleteGraph = async (graphId: string) => {
  const response = await api.delete(`/api/graphs/${graphId}`);
  return response.data;
};
