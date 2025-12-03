## 🔴 페이지 3 I2I 이미지 스타일 변경 - 버그 분석 결과

### 문제 현상
- 서로 다른 입력 이미지를 주어도 거의 동일한 내용과 스타일의 이미지가 생성됨
- 프롬프트가 제대로 반영되지 않는 것 같음
- 입력 이미지가 제대로 사용되지 않는 것 같음

---

## ✅ 발견된 버그

### 🐛 버그 1: 입력 이미지 노드 ID 불일치

**파일**: `src/backend/services.py` (라인 803)

**문제코드**:
```python
# ComfyUI 실행 (입력 이미지 포함)
output_images, history = client.execute_workflow(
    workflow=workflow,
    input_image=input_image_bytes,
    input_image_node_id="11"  # ❌ 잘못된 노드 ID!
)
```

**왜 문제인가?**
- I2I 워크플로우의 LoadImage 노드는 "5"
- 그런데 코드에서 "11"을 지정함
- 결과: 입력 이미지가 워크플로우의 노드 11에 설정되는데, 이 노드는 존재하지 않음
- 따라서 입력 이미지가 무시되고, 기본값(또는 이전 캐시된 이미지)이 사용됨

**해결책**:
```python
# ComfyUI 실행 (입력 이미지 포함)
output_images, history = client.execute_workflow(
    workflow=workflow,
    input_image=input_image_bytes,
    input_image_node_id="5"  # ✅ 올바른 노드 ID
)
```

**상태**: ✅ 수정 완료 (2025-12-03)

---

### 🐛 버그 2: 워크플로우별 입력 노드 ID 일관성 문제

**파일**: `src/backend/comfyui_workflows.py` (라인 710)

**문제코드**:
```python
def get_workflow_input_image_node_id(experiment_id: str) -> str:
    """워크플로우의 입력 이미지 노드 ID 반환"""
    # 모든 워크플로우에서 노드 1이 LoadImage
    return "1"  # ❌ 틀림!
```

**왜 문제인가?**
- 기본 I2I 워크플로우 (페이지 3): LoadImage 노드는 "5"
- 고급 편집 모드 워크플로우 (페이지 4): LoadImage 노드는 "1"
- 하지만 함수에서는 항상 "1"을 반환함
- 결과: 페이지 3에서 입력 이미지 노드를 찾지 못함

**해결책**:
```python
def get_workflow_input_image_node_id(experiment_id: str) -> str:
    """워크플로우의 입력 이미지 노드 ID 반환"""
    # 기본 I2I 워크플로우 (페이지 3): 노드 5가 LoadImage
    if experiment_id in [None, "", "i2i", "basic_i2i"]:
        return "5"
    
    # 고급 편집 모드 워크플로우 (페이지 4): 노드 1이 LoadImage
    return "1"
```

**상태**: ✅ 수정 완료 (2025-12-03)

---

## 📝 추가 개선사항

### 3. 디버깅 로그 추가

**파일**: `src/backend/services.py` (라인 731)

**추가된 로그**:
```python
# 📊 입력 이미지 및 프롬프트 검증 (디버깅)
logger.info(f"📸 입력 이미지 크기: {len(input_image_bytes)} bytes")
logger.info(f"📝 원본 프롬프트: {prompt[:100] if prompt else 'N/A'}...")
logger.info(f"💪 Strength: {strength}")

print(f"✏️ ComfyUI로 I2I 이미지 편집 중")
print(f"   모델: {current_model_name}")
print(f"   원본 프롬프트: {prompt[:80]}...")
print(f"   최종 프롬프트: {final_prompt[:80]}...")
```

**목적**:
- 입력 이미지 크기 추적
- 원본 프롬프트와 최종 프롬프트 비교
- Strength 값 검증

---

## 🔍 검증 방법

### 1. 로그 확인
```bash
tail -f logs/uvicorn.log | grep -E "입력 이미지|프롬프트|Strength"
```

### 2. 테스트 실행
```bash
python test_i2i_debug.py
```

이 테스트는:
- 3가지 서로 다른 입력 이미지 생성
- 각각에 다른 프롬프트 적용
- 출력 이미지 비교 (입력과 동일하면 경고)

### 3. 수동 테스트
1. 페이지 3으로 이동
2. 빨간색 배경 이미지 업로드 + "파란색 배경으로 변경" 프롬프트
3. 다시 초록색 배경 이미지 업로드 + "노란색 배경으로 변경" 프롬프트
4. **결과**: 완전히 다른 이미지가 생성되어야 함

---

## 📊 예상 개선 효과

| 항목 | 이전 | 개선 후 |
|------|------|--------|
| 입력 이미지 반영 | ❌ 무시됨 | ✅ 적용됨 |
| 프롬프트 적용 | ⚠️ 부분 적용 | ✅ 완전 적용 |
| 스타일 변경 | ❌ 동일 결과 | ✅ 다양한 결과 |
| 디버깅 정보 | ❌ 불충분 | ✅ 상세 로깅 |

---

## 📋 관련 코드 변경사항

### 변경된 파일
1. **src/backend/services.py**
   - 라인 803: `input_image_node_id="11"` → `input_image_node_id="5"`
   - 라인 731-745: 디버깅 로그 추가

2. **src/backend/comfyui_workflows.py**
   - 라인 710-723: `get_workflow_input_image_node_id()` 함수 개선

### 테스트 파일
- **test_i2i_debug.py**: 페이지 3 I2I 디버깅 테스트 스크립트

---

## ⚠️ 주의사항

1. **모델 선택 필수**: 페이지 3 사용 전 사이드바에서 모델(flux_dev 등) 선택 필수
2. **ComfyUI 실행**: ComfyUI 서버가 실행 중이어야 함
3. **GPU 메모리**: I2I 편집에 충분한 GPU 메모리 필요 (약 16GB+)

---

## 🚀 다음 단계

1. ✅ 버그 수정 코드 배포
2. ⏳ 로컬 테스트 (test_i2i_debug.py)
3. ⏳ 프로덕션 환경 재배포
4. ⏳ 사용자 피드백 수집

---

**마지막 업데이트**: 2025-12-03
**수정된 버전**: v1.0.1 (I2I 버그 수정)
