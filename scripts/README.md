# 단위 테스트·점검 스크립트

## 1. 개요

- 역할: 웹 화면·서버 없이 AI 모듈(SAM2, AnyDoor) 단독 실행, 개발 환경 점검
- 실행 위치: 저장소 최상위 디렉터리 (PowerShell)
- 실행 환경: 가상환경 `CGI` ([environment.md](../docs/environment.md))

| 스크립트 | 용도 | 필요 모델 |
|---|---|---|
| `check_env.py` | 개발 환경 점검 | - |
| `test_object_extraction.py` | 상의 영역 추출 단독 실행 | SAM2 |
| `test_compose.py` | 이미지 합성 단독 실행 | AnyDoor |

## 2. check_env.py (개발 환경 점검)

```powershell
CGI\Scripts\python.exe scripts\check_env.py
```

- 점검: Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 모델 가중치, `backend/.env`
- 판정 기준: [environment.md 3. 설치 확인](../docs/environment.md#3-설치-확인)

## 3. test_object_extraction.py (상의 영역 추출)

```powershell
CGI\Scripts\python.exe scripts\test_object_extraction.py 상의.jpg --points "487,731;483,443" --out mask.png
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
CGI\Scripts\python.exe scripts\test_compose.py --garment 상의.jpg --garment-mask mask.png --person 인물.jpg --area 착용영역.png --out compose.jpg
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
