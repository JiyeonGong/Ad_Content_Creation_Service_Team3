# 프로젝트 종합 리뷰 (2025-12-03)

## 프로젝트 의도와 구현 적합성
- 아키텍처: `Streamlit (8501) ↔ FastAPI (8000) ↔ ComfyUI (8188)` 3-티어 구조. 이미지 생성/편집은 ComfyUI, 문구/프롬프트 최적화는 OpenAI GPT.
- 페이지별 목적 대비 구현 상태
  - 페이지 1 (문구 생성): `generate_caption_core` 존재. 포맷 지시 포함, GPT 미설정 시 폴백 필요 확인.
  - 페이지 2 (T2I): 프론트 설정(사이즈/스텝/가이던스) 완비. 백엔드 `generate_t2i_core`는 ComfyUI 통합 리팩토링 중(일부 미완성 분기 존재).
  - 페이지 3 (I2I): UI 완비(Strength/Steps/Guidance/ADetailer). 백엔드 `generate_i2i_core`는 리팩토링 중으로 ComfyUI 호출부 일부 미완성.
  - 페이지 4 (이미지 편집/실험): 모드 정의(인물/제품/하이브리드) 및 페이로드 설계 완료. 백엔드 `edit_image_with_comfyui` 스텁 상태.
  - 페이지 5 (캘리그라피): 요구 반영 완료. 기본 모드 Pillow(투명 PNG), 스타일 모드 SDXL+ControlNet+Rembg. 기본 폰트 자동 `/home/shared/RiaSans-Bold.ttf`.
- 서비스 레이어: ModelLoader 중심 모델 관리/전환 의도. ComfyUI 모델 상태 추적/언로드 유틸 스텁 존재. 프롬프트 최적화(FLUX 3단계 + v2 통합)는 일부 미완성.

## 디버깅/구조적 점검 결과
- 컴파일 상태: `src/frontend/app.py`, `src/backend/services.py` 모두 Python 구문 검사 통과.
- 잠재 이슈
  - 미완성 함수 블록: `optimize_prompt`, `build_final_prompt_v2`, `build_final_prompt`, `generate_t2i_core`, `generate_i2i_core`, `apply_adetailer`, `edit_image_with_comfyui`, `get_image_editing_experiments`, ComfyUI 상태/언로드 함수들에 빈 분기 존재 → 호출 시 런타임 실패 위험.
  - VRAM 메모리: ComfyUI 모델 언로드/캐시 해제가 부족. 연속 페이지 사용 시 OOM 가능. 캘리그라피 기본 모드는 안전, 스타일 모드는 위험 가능.
  - 경로 의존성: `/home/shared/RiaSans-Bold.ttf` 고정. 환경에 따라 폰트 없을 수 있음 → 대체 폰트 폴백 필요.
  - 예외 일관성: 일부 함수 `RuntimeError` 직접 사용, 일부는 `ImageProcessingError` 등 커스텀 예외 사용 → 표준화 필요.
  - 프론트/백엔드 페이로드 일치: `post_process_method`, `model_name` 등 필드의 소비 확인/검증 필요.
  - 중복 코드/주석: services.py에 프롬프트 최적화 구버전 주석 다수 → 가독성 저하.

## 진행 상황 요약
- 프론트엔드: 페이지 1/3/5는 목적 대비 동작 완성도 높음. 페이지 5 최신 요구 반영 완료.
- 백엔드: 캘리그라피는 안정 작동. T2I/I2I/편집(실험 모드)은 ComfyUI 통합 리팩토링 진행 중으로 핵심 함수 일부 미완성.
- 문서: README의 일부 과거 상태가 되돌려져 최신 기능과 불일치 가능.

### 페이지 5 추가 메모
- CLIP 77 토큰 이슈가 남아 있으나, 최근 개선으로 캘리그라피 생성(기본 Pillow/스타일 AI) 안정성이 향상되었습니다. 일반 사용 시 생성 자체는 큰 문제 없이 수행됩니다.

## 문제점 및 리스크
- 기능 일관성: 프론트 페이로드 ↔ 백엔드 처리 불일치 가능.
- 메모리 관리: ComfyUI 모델 언로드 미흡으로 VRAM OOM 위험.
- 호출 경로 안정성: 미완성 함수 호출 시 예외 발생 위험.
- 환경 의존성: `/home/shared` 경로 고정으로 폰트/모델 불가 시 실패.

## 추후 개선 로드맵
1) ComfyUI 모델 라이프사이클
- 모델 전환 시 이전 모델 언로드, `torch.cuda.empty_cache()` 호출.
- 페이지 전환 시 백엔드 클린업 훅 연동.

2) 워크플로우 유효성 검증/테스트
- `get_workflow_*` 로드 시 노드/입력 키 검증.
- 모드별 단위 테스트 및 최소 실행 테스트 추가.

3) 설정 중앙화
- 폰트/모델/경로를 `configs/*.yaml`로 통합.
- 환경별 오버라이드/폴백(`cache/hf_models`) 구성.

4) 예외/로깅 표준화
- 모든 서비스 함수에서 커스텀 예외 사용으로 일관화.
- 성능/메모리/시간 측정 로깅 추가.

5) 프롬프트 최적화 마무리
- `build_final_prompt_v2` 단일 호출 완성 후 구버전 정리.
- GPT 비활성 시 폴백 규칙 정의.

6) E2E 시나리오 테스트
- Caption→T2I→I2I→Calligraphy 순서 실행 스크립트 작성.
- 성공/시간/메모리 로그 수집.

7) 폰트/리소스 폴백
- 기본 폰트 존재 확인 후 대체(예: DejaVuSans) 자동 폴백.

## 즉시 수행 권장 작업 (우선순위)
- High: `generate_t2i_core`, `generate_i2i_core`, `edit_image_with_comfyui` 구현 마무리 및 ComfyUI 모델 언로드 유틸 완성.
- Medium: 프론트 페이로드 ↔ 백엔드 엔드포인트 일치 확인/수정, 프롬프트 v2 통합 마무리.
- Low: services.py 주석/구버전 정리, README 최신화.

## 참고 로그/현황
- 최근 명령: ComfyUI 서버 백그라운드 실행, 백엔드 구문검사, 프론트 구문검사 모두 성공.
- Known Issue: Page 4 실험 모드 요청은 테스트 스크립트 존재하나 백엔드 처리 스텁 상태로 실제 성공은 구현 완료 후 가능.

---
작성자: 프로젝트 매니저 (자동 기록)
브랜치: localbjs3
