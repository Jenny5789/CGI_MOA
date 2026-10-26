# 단위 테스트·점검 스크립트

## 1. 개요

- 역할: 웹 화면·서버 없이 AI 모듈(SAM2, AnyDoor) 단독 실행, 개발 환경 점검, 화면 예시 이미지 줄이기
- 실행 위치: 저장소 최상위 디렉터리 (PowerShell)
- 실행 환경: conda 환경 `CGI`, 실행 전 `conda activate CGI`. 구축: [README 9. 설치 및 실행](../README.md#9-설치-및-실행)

| 스크립트 | 용도 | 필요 모델 |
|---|---|---|
| `check_env.py` | 개발 환경 점검 | - |
| `test_object_extraction.py` | 상의 영역 추출 단독 실행 | SAM2 |
| `test_compose.py` | 이미지 합성 단독 실행 | AnyDoor |
| `compress_web_images.py` | 화면 예시 생성 이미지를 웹용 JPG로 줄이기 | - |
| `preprocess_shapeless.py` | 쉐이프리스 데이터를 AnyDoor 학습용으로 변환 | - |

## 2. check_env.py (개발 환경 점검)

```powershell
python scripts\check_env.py
```

- 점검: Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 모델 가중치, `backend/.env`
- 판정 기준: [README 설치 7. 설치 확인](../README.md#설치-7-설치-확인)

## 3. test_object_extraction.py (상의 영역 추출)

```powershell
python scripts\test_object_extraction.py 상의.jpg --points "487,731;483,443" --out mask.png
```

| 옵션 | 필수 | 설명 |
|---|---|---|
| 첫 인자 | O | 상의 이미지 경로 |
| `--points` | 조건 | 포함 점 `x,y` (원본 픽셀, 여러 개는 `;`로 구분) |
| `--neg` | - | 제외 점 (형식 같음) |
| `--box` | 조건 | 상의를 감싸는 사각형 `x1,y1,x2,y2` |
| `--out` | - | 결과 파일 (기본 `mask.png`) |

- 조건: `--points`, `--neg`, `--box` 중 1개 이상
- 결과: 흑백 PNG (흰색: 상의 영역)

## 4. test_compose.py (이미지 합성)

```powershell
python scripts\test_compose.py --garment 상의.jpg --garment-mask mask.png --person 인물.jpg --area 착용영역.png --out compose.jpg
```

| 옵션 | 필수 | 설명 |
|---|---|---|
| `--garment` | O | 상의 이미지 |
| `--garment-mask` | O | 상의 영역 흑백 PNG (3. 결과 사용) |
| `--person` | O | 인물 이미지 |
| `--area` | O | 착용 영역 흑백 PNG (흰색: 합성 위치) |
| `--out` | - | 결과 파일 (기본 `compose.jpg`) |
| `--seed` | - | 같은 값이면 같은 결과 (기본 1234) |

- 결과: 상의 | 인물 | 합성 결과를 나란히 붙인 이미지, 소요 시간·최대 GPU 메모리 출력

## 5. compress_web_images.py (화면 예시 이미지 줄이기)

```powershell
python scripts\compress_web_images.py
```

- 원본: `generated_assets/<묶음>/*.png` (1254×1254, 장당 약 2MB, 저장소에 올리지 않음)
- 결과: `frontend/public/assets/generated/<묶음>/*.jpg` (긴 변 1024px, 품질 85), 합성하기 예시 4묶음은 `thumb/*.jpg`도 만듦 (긴 변 240px, 예시 줄·"더보기" 창용)
- 묶음 목록: 스크립트 안 `FOLDERS` (화면이 쓰는 묶음, `frontend/src/data/generatedAssets.js`와 맞춤). 생성 이미지를 바꾸면 원본을 `generated_assets/`에 두고 다시 실행 (결과 덮어씀)
- 출력: 묶음별 장수, 원본 → 결과 용량

## 6. preprocess_shapeless.py (쉐이프리스 → AnyDoor 학습용)

```powershell
python scripts\preprocess_shapeless.py --limit 200
python scripts\preprocess_shapeless.py
```

- 입력: `Downloads\011.쉐이프리스 의류 및 포즈 데이터\01-1.정식개방데이터\Training` (원천데이터 jpg 압축 해제본, 라벨링데이터 zip 그대로). 경로가 다르면 `--src`
- 결과: `Dataset\Shapeless_AnyDoor\Training\` 아래 VITON-HD와 같은 구조 (768×1024)
  - `cloth` 제품 사진, `cloth-mask` 제품 마스크, `image` 착용 사진, `image-parse-v3` 옷 영역 (옷=5)
  - `pairs.jsonl` 쌍별 정보(모델·포즈·각도·옷 비율), `report.json` 처리·건너뜀 집계
- 사람(제품은 옷) 영역을 3:4로 먼저 잘라 줄임 (`--crop-margin`, 전체를 줄이려면 -1). 전신 사진이라 그대로 줄이면 옷이 작아져 AnyDoor 학습 해상도가 떨어짐
- 이어서 처리: 이미 만든 파일은 건너뜀. 압축 해제 중이라 원천 이미지가 없는 쌍은 `report.json`의 `missing_image`로 집계, 해제가 끝난 뒤 같은 명령으로 이어서 처리
- 건너뛰는 쌍: 옷 영역 비율이 0.01~0.64 밖(AnyDoor `check_mask_area`와 같음), 제품 JSON과 착용 JSON의 옷 종류가 다름, 라벨 크기가 이미지와 다름
- 제품 사진은 NTFS 하드링크로 연결해 용량을 아낌 (복사하려면 `--no-hardlink`)
- 학습 연결: `checkpoints/AnyDoor/configs/datasets.yaml`의 `VitonHD.image_dir`를 `C:/CGI_MOA/Dataset/Shapeless_AnyDoor/Training/cloth/` 로 지정 (끝의 `/` 필수)
- 라벨 JSON 특이점: 모든 클래스 키가 같은 폴리곤 목록을 반복하며 키 순서와 폴리곤 순서가 1:1 대응. 한 클래스가 여러 조각이면 대응이 깨져서(약 15%), 코·눈·귀 키포인트가 든 얼굴 폴리곤 앞쪽을 옷 조각으로 처리
