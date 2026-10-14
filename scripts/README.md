# scripts

- 서버·화면 없이 AI 기능만 확인하는 스크립트
- 실행 위치: 저장소 맨 위 폴더
- 실행 환경: SAM2가 설치된 `CGI` 가상환경 (설치 방법: [../docs/environment.md](../docs/environment.md))
- 모델 파일 필요 (저장소에 없음)
  - SAM2: `checkpoints/sam2/sam2.1_hiera_base_plus.pt` → [../features/object_extraction/README.md](../features/object_extraction/README.md)
  - AnyDoor (합성 확인 때만): [../features/composition/README.md](../features/composition/README.md)

| 스크립트 | 용도 |
|---|---|
| `test_object_extraction.py` | 사진 1장에 점 또는 박스를 줘서 SAM2 상의 윤곽 확인 |
| `test_compose.py` | 옷·옷 윤곽·인물·입힐 영역 4장으로 AnyDoor 합성 확인, 걸린 시간·GPU 메모리 출력 |

## test_object_extraction.py

- 명령: `python scripts/test_object_extraction.py <사진 경로> --points "x1,y1;x2,y2" --out mask.png`
- `--points`: 상의 위 포함 점 (원본 픽셀 좌표, 여러 개는 `;`로 구분)
- `--neg`: 제외할 곳 점 (선택)
- `--box`: 상의를 감싸는 박스 `x1,y1,x2,y2` (선택)
- 결과: 흑백 윤곽 PNG (흰색 = 상의)

## test_compose.py

- 명령: `python scripts/test_compose.py --garment 옷.jpg --garment-mask 옷윤곽.png --person 인물.jpg --area 입힐영역.png --out compose.jpg`
- 옷 윤곽: `test_object_extraction.py` 결과 그대로 사용
- 입힐 영역: 흑백 PNG (흰색 = 입힐 곳), 인물 사진과 크기가 다르면 자동으로 맞춤
- `--seed`: 같은 값이면 같은 결과 (기본 1234)
- 결과: 옷 사진 | 인물 사진 | 합성 결과를 나란히 붙인 그림
