# scripts

- 서버·화면 없이 AI 기능만 시험
- 실행: 저장소 맨 위 폴더, `CGI` 가상환경
- 모델 파일 필요: SAM2([설명](../features/object_extraction/README.md)), AnyDoor([설명](../features/composition/README.md), 합성 시험만)

## test_object_extraction.py (SAM2 추출)

- `python scripts/test_object_extraction.py 사진.jpg --points "x1,y1;x2,y2" --out mask.png`
- `--points`: 포함 점 (원본 픽셀, `;`로 구분)
- `--neg`: 제외 점 (선택) / `--box`: `x1,y1,x2,y2` (선택)
- 결과: 흑백 윤곽 PNG (흰색 = 상의)

## test_compose.py (AnyDoor 합성)

- `python scripts/test_compose.py --garment 옷.jpg --garment-mask 옷윤곽.png --person 인물.jpg --area 입힐영역.png --out compose.jpg`
- 옷 윤곽: `test_object_extraction.py` 결과
- 입힐 영역: 흑백 PNG (흰색 = 입힐 곳)
- `--seed`: 기본 1234 (같으면 같은 결과)
- 결과: 옷 | 인물 | 합성 나란히, 걸린 시간·GPU 메모리 출력

## check_env.py (개발 환경 점검)

- `python scripts/check_env.py`
- 점검: 가상환경, Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 모델 가중치, `backend/.env`
- 기준·조치: [../docs/environment.md](../docs/environment.md) "3. 설치 확인"
