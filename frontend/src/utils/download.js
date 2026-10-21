/* 합성 결과 다운로드: 서버가 준 결과 주소(image_url, 열쇠 포함)에서 파일을 받아 "MOA_날짜_시각" 이름으로 저장한다 */
import { formatKoreanDate } from './date.js';

const fileName = (item, type) => {
  const stamp = formatKoreanDate(item.created_at).replace(/[.:]/g, '').replace(' ', '_'); // 20261020_1432
  return `MOA_${stamp}.${type === 'image/jpeg' ? 'jpg' : 'png'}`;
};

export async function downloadResult(item) {
  const res = await fetch(item.image_url);
  if (!res.ok) throw new Error('사진을 받지 못했습니다. 마이페이지를 새로고침한 뒤 다시 시도해 주십시오');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName(item, blob.type);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
