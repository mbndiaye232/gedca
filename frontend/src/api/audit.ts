import { api } from './client';
import type { PageAuditLog } from './types';

export interface AuditQuery {
  action?: string;
  entite?: string;
  debut?: string; // ISO datetime
  fin?: string;
  limit?: number;
  offset?: number;
}

export async function listerAuditLog(params: AuditQuery = {}): Promise<PageAuditLog> {
  const { data } = await api.get<PageAuditLog>('/audit-log', { params });
  return data;
}
