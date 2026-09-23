# MOA 기술 설계 결정 기록

## 1. ComfyUI 활용 범위

### 논의 배경

현재 BiRefNet과 SAM2의 기능 검증은 ComfyUI에서 진행했다.

향후 MOA 서비스에 AI 기능을 적용할 때 다음 방식 중 어떤 구조를 사용할지 결정이 필요하다.

### 방식 A — ComfyUI는 기술 검증용으로만 사용

구조:

MOA → Python 코드 → AI Model

장점:
- 최종 서비스가 ComfyUI에 의존하지 않음
- Python 코드에서 모델 입력·출력과 후처리를 직접 제어하기 쉬움
- 기능 수정과 디버깅 위치가 명확함

단점:
- ComfyUI에서 검증한 Workflow를 Python 코드로 다시 연결해야 함
- 모델별 로딩·전처리·추론·후처리를 직접 구현해야 함
- 초기 개발 시간이 더 필요할 수 있음


### 방식 B — ComfyUI를 실제 AI 실행 엔진으로 사용

구조:

MOA UI → Backend → ComfyUI Workflow → AI Model

장점:
- 검증한 Workflow를 실제 서비스에서도 활용 가능
- 여러 AI 모델과 처리 단계를 빠르게 연결할 수 있음
- 초기 프로토타입 구현 속도가 빠를 수 있음

단점:
- 최종 서비스가 ComfyUI 실행 환경에 의존함
- 배포 시 ComfyUI, Custom Node, Model, Checkpoint, Workflow 등의 환경 관리가 필요함
- MOA Backend와 ComfyUI 사이의 요청·결과 전달 구조가 추가됨
- 세부 기능을 수정할 때 ComfyUI 구조도 함께 고려해야 함


### 방식 C — 혼합 방식

예:

사람 추출
→ BiRefNet Python 직접 실행

복잡한 이미지 생성/합성
→ ComfyUI Workflow 활용

장점:
- 단순한 기능은 직접 제어 가능
- 복잡한 Workflow는 기존 구조를 재활용 가능

단점:
- Python 실행 방식과 ComfyUI 실행 방식을 모두 관리해야 함
- 전체 시스템 구조가 복잡해질 수 있음


### 현재 상태

- BiRefNet / SAM2: ComfyUI에서 기능 검증 완료
- 사람 추출 1차 후보: BiRefNet
- 최종 서비스에서 ComfyUI를 사용할지는 미결정
- 다른 합성 기능 검증 결과와 개발 기간을 함께 고려하여 결정 예정

### 팀 논의 필요 사항

- 프로젝트 기간 내 Python 직접 구현 범위
- ComfyUI Workflow 재사용 필요성
- 최종 배포 방식
- 유지보수 및 기능 수정 편의성
- 팀원이 구현 중인 UI/Backend와의 연결 방식

### 결정

미정