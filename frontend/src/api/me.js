import { request } from './client.js';

// 명세 2-3
export function getMe() {
  return request('GET', '/me');
}
