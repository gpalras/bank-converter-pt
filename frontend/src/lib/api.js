// frontend/src/lib/api.js
import axios from "axios";

const baseURL = process.env.REACT_APP_BACKEND_URL || "";

const api = axios.create({ baseURL });

// Interceptor: adiciona automaticamente o token JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
