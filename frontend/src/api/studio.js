/* 합성하기 화면이 쓰는 서버 요청 (명세 3~5장). 실제 서버(backend/)가 대답한다 (client.js의 mixed 모드). */
import { request } from './client.js';

// 명세 3-1. 화면에 보이는 사진 주소(src)에서 파일을 꺼내 올린다. kind: 'garment' 상의 사진 / 'person' 인물 사진
// fromSample: 예시 사진에서 고른 것이면 true (최근 사용한 사진 목록에 넣지 않음)
export async function uploadImage(src, kind, fromSample = false) {
  const blob = await fetch(src).then((r) => r.blob());
  const form = new FormData();
  form.append('file', blob, blob.type === 'image/png' ? 'image.png' : 'image.jpg');
  form.append('kind', kind);
  form.append('from_sample', fromSample ? '1' : '0');
  return request('POST', '/images', form); // { image_id, url, width, height }
}

// 명세 3-2. 최근 24시간 동안 직접 올린 사진 → [{ image_id, url, thumb_url, width, height, created_at }] 최신순
export async function listRecentImages(kind) {
  const data = await request('GET', `/images/recent?kind=${kind}`);
  return data.items;
}

// 명세 4-1. points: [{ x, y, label }] (0~1 비율, label 1 포함 / 0 제외)
export function extractGarment(imageId, points) {
  return request('POST', '/extract', { image_id: imageId, points }); // { extraction_id, mask_url, cutout_url, bbox }
}

// 명세 5-1. areaMask: 입힐 영역 흑백 PNG(Blob, 칠한 곳 흰색)
// garmentMask: 3단계 다듬기에서 고친 상의 윤곽 흑백 PNG (없으면 서버가 SAM2 윤곽을 씀)
// refine: 상의 경계 다듬기, shapeControl: 칠한 모양 그대로 (합성 설정 팝업)
export function requestCompose(extractionId, personImageId, areaMask, { garmentMask = null, refine = false, shapeControl = false } = {}) {
  const form = new FormData();
  form.append('extraction_id', extractionId);
  form.append('person_image_id', personImageId);
  form.append('area_mask', areaMask, 'area.png');
  if (garmentMask) form.append('garment_mask', garmentMask, 'garment.png');
  form.append('refine', refine ? '1' : '0');
  form.append('shape_control', shapeControl ? '1' : '0');
  return request('POST', '/compose', form); // { job_id, status, queue_position }
}

// 명세 5-2, 5-3
export const getJob = (jobId) => request('GET', `/jobs/${encodeURIComponent(jobId)}`);
export const getResult = (resultId) => request('GET', `/results/${encodeURIComponent(resultId)}`);

// 결과를 만든 재료 (명세 외 추가 제안): 상의·인물 사진, 상의 윤곽, 입힐 영역, 합성 설정. 내 작업 기록에서 1~4단계를 채울 때 쓴다
export const getResultSource = (resultId) => request('GET', `/results/${encodeURIComponent(resultId)}/source`);
