/**
 * Client axios partagé.
 *
 * - Injection automatique du Bearer token depuis localStorage.
 * - Sur 401, purge le token et redirige vers /login.
 * - Extraction homogène des messages d'erreur via `extraireMessageErreur`.
 */

import axios, { AxiosError, type AxiosInstance } from 'axios';
import type { ApiError } from './types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

const TOKEN_KEY = 'gedca_token';
const AGENT_KEY = 'gedca_agent';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(AGENT_KEY);
}

export function getStoredAgent<T>(): T | null {
  const raw = localStorage.getItem(AGENT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function setStoredAgent(agent: unknown): void {
  localStorage.setItem(AGENT_KEY, JSON.stringify(agent));
}

export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 401 → token invalide/expiré : purge et reload vers /login
    if (error.response?.status === 401) {
      const onLoginPage = window.location.pathname === '/login';
      if (!onLoginPage) {
        clearToken();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

/** Extrait un message d'erreur lisible depuis une réponse Axios. */
export function extraireMessageErreur(err: unknown, fallback = 'Erreur inattendue'): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as ApiError | { detail?: Array<{ msg?: string }> } | undefined;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.detail)) {
      // erreur de validation Pydantic
      return data.detail.map((e) => e.msg ?? '').filter(Boolean).join(' ; ') || fallback;
    }
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
