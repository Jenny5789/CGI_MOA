/* 합성하기 화면이 쓰는 서버 요청 (명세 3~5장). 실제 서버(backend/)가 대답한다 (client.js의 mixed 모드). */
import { request } from './client.js';

// 명세 3-1. 화면에 보이는 사진 주소(src)에서 파일을 꺼내 올린다. kind: 'garment' 상의 사진 / 'person' 인물 사진
export async function uploadImage(src, kind) {
  const blob = await fetch(src).then((r) => r.blob());
  const form = new FormData();
  form.append('file', blob, blob.type === 'image/png' ? 'image.png' : 'image.jpg');
  form.append('kind', kind);
  return request('POST', '/images', form); // { image_id, url, width, height }
}

// 명세 4-1. points: [{ x, y, label }] (0~1 비율, label 1 포함 / 0 제외)
export function extractGarment(imageId, points) {
  return request('POST', '/extract', { image_id: imageId, points }); // { extraction_id, mask_url, cutout_url, bbox }
}

// 명세 5-1. areaMask: 입힐 영역 흑백 PNG(Blob, 칠한 곳 흰색)
export function requestCompose(extractionId, personImageId, areaMask) {
  const form = new FormData();
  form.append('extraction_id', extractionId);
  form.append('person_image_id', personImageId);
  form.append('area_mask', areaMask, 'area.png');
  return request('POST', '/compose', form); // { job_id, status, queue_position }
}

// 명세 5-2, 5-3
export const getJob = (jobId) => request('GET', `/jobs/${encodeURIComponent(jobId)}`);
export const getResult = (resultId) => request('GET', `/results/${encodeURIComponent(resultId)}`);
