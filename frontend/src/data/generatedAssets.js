// 웹용으로 줄인 JPG (원본 PNG에서 scripts/compress_web_images.py로 만든다)
const paths = (folder, prefix, count) => Array.from(
  { length: count },
  (_, i) => `/assets/generated/${folder}/${prefix}_${String(i + 1).padStart(3, '0')}.jpg`,
);

// 합성하기 예시 묶음의 작은 사진(긴 변 240px) 주소: 예시 줄과 "더보기" 창에만 쓰고, 고르면 원래 크기 사진을 쓴다
export const thumbOf = (src) => src.replace(/\/([^/]+)$/, '/thumb/$1');

export const topsOnly = paths('tops_only_30', 'top', 30);
export const topsWorn = paths('tops_worn_30', 'worn', 30);
export const baseModels = paths('base_models_30', 'model', 30);
export const fullBodyModels = paths('full_body_models_30', 'model', 30);
export const showcaseTops = paths('showcase_tops_30', 'top', 30);

// 홈 화면: 위쪽 예시(같은 번호의 상의, 모델, 결과가 한 세트)와 기능 소개 사진.
export const curatedResults = paths('curated_results_8', 'result', 8);
export const curatedBackgrounds = paths('curated_backgrounds_8', 'model', 8);
export const featureLifestyle = paths('feature_lifestyle_3', 'feature', 3);
