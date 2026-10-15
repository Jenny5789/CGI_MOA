import { request } from './client.js';

// 명세 6-1. filters: { saved, favorite, date: 'YYYY-MM-DD', sort: 'new' | 'old' }. 비어 있는 조건은 보내지 않는다
export function listResults(filters = {}) {
  const q = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)); });
  const qs = q.toString();
  return request('GET', '/results' + (qs ? `?${qs}` : ''));
}

// 명세 6-2. patch: { saved: true } 또는 { favorite: true|false }
export function updateResult(resultId, patch) {
  return request('PATCH', `/results/${encodeURIComponent(resultId)}`, patch);
}
