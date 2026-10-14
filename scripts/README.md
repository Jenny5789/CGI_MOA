# scripts

- 서버·화면 없이 AI 기능만 확인하는 스크립트
- 실행 위치: 저장소 맨 위 폴더
- 실행 환경: SAM2가 설치된 `CGI` 가상환경 (설치 방법: [../docs/environment.md](../docs/environment.md))
- SAM2 모델 파일 필요: `checkpoints/sam2/sam2.1_hiera_base_plus.pt` (저장소에 없음, 위치는 [../features/object_extraction/README.md](../features/object_extraction/README.md) 참고)

| 스크립트 | 용도 |
|---|---|
| `test_object_extraction.py` | 사진 1장에 점 또는 박스를 줘서 SAM2 상의 윤곽 확인 |

## test_object_extraction.py

- 명령: `python scripts/test_object_extraction.py <사진 경로> --points "x1,y1;x2,y2" --out mask.png`
- `--points`: 상의 위 포함 점 (원본 픽셀 좌표, 여러 개는 `;`로 구분)
- `--neg`: 제외할 곳 점 (선택)
- `--box`: 상의를 감싸는 박스 `x1,y1,x2,y2` (선택)
- 결과: 흑백 윤곽 PNG (흰색 = 상의)
