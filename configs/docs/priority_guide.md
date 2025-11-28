# 설정 우선순위 가이드

## 🎯 우선순위 체계

```
1순위: 환경변수 (.env 또는 시스템)        ← 최우선! 🥇
2순위: YAML 설정 파일                      ← 기본값  🥈
3순위: 코드 내 하드코딩된 폴백 값          ← 최후의 수단 🥉
```

---

## 📊 실제 동작 예시

### 시나리오 1: .env만 설정한 경우

```bash
# .env
PRIMARY_MODEL=flux-schnell
```

```yaml
# model_config.yaml
runtime:
  primary_model: "sdxl"  # 무시됨!
```

**결과:** `flux-schnell` 사용 ✅

---

### 시나리오 2: YAML만 설정한 경우

```bash
# .env
# (PRIMARY_MODEL 없음)
```

```yaml
# model_config.yaml
runtime:
  primary_model: "sdxl"  # 이게 사용됨!
```

**결과:** `sdxl` 사용 ✅

---

### 시나리오 3: 둘 다 설정한 경우

```bash
# .env
PRIMARY_MODEL=playground  # 이게 우선!
```

```yaml
# model_config.yaml
runtime:
  primary_model: "flux-schnell"  # 무시됨
```

**결과:** `playground` 사용 ✅

---

### 시나리오 4: 둘 다 없는 경우

```bash
# .env
# (PRIMARY_MODEL 없음)
```

```yaml
# model_config.yaml
runtime:
  # primary_model 없음
```

**결과:** 코드의 기본값 `"sdxl"` 사용 (폴백) ✅

---

## 🔍 코드에서 실제 구현

### model_registry.py
```python
def get_primary_model(self) -> str:
    """환경변수 또는 설정 파일에서 기본 모델 이름 가져오기"""
    return os.getenv(
        "PRIMARY_MODEL",  # 1순위: 환경변수 확인
        self.runtime_config.get("primary_model", "sdxl")  # 2순위: YAML
    )
```

이 코드가 우선순위를 결정합니다!

---

## 💡 사용 권장 사항

### ✅ 추천: 역할 분담

#### YAML 파일 (.yaml)
- **용도**: 팀 공유 기본 설정
- **관리**: Git으로 버전 관리
- **예시**: 개발팀 모두가 사용할 기본 모델

```yaml
# model_config.yaml - Git 커밋 ✅
runtime:
  primary_model: "sdxl"  # 팀 기본값
  fallback_models:
    - "playground"
```

#### 환경변수 (.env)
- **용도**: 개인/환경별 오버라이드
- **관리**: Git 제외 (.gitignore)
- **예시**: 개발자마다 다른 모델 테스트

```bash
# .env - Git 커밋 ❌
PRIMARY_MODEL=flux-schnell  # 내 개인 설정
```

---

## 🎬 실전 시나리오

### 개발 팀 협업 예시

#### 상황
- 팀 기본값: SDXL (안정적)
- Alice: FLUX 테스트 중
- Bob: Playground 선호
- 프로덕션: FLUX 사용

#### 설정

**공통 (Git 커밋)**
```yaml
# model_config.yaml
runtime:
  primary_model: "sdxl"  # 팀 기본
```

**Alice 로컬**
```bash
# Alice의 .env
PRIMARY_MODEL=flux-schnell  # Alice만 FLUX
```

**Bob 로컬**
```bash
# Bob의 .env
PRIMARY_MODEL=playground  # Bob만 Playground
```

**프로덕션 서버**
```bash
# 서버 환경변수
export PRIMARY_MODEL=flux-schnell
export USE_8BIT=false
```

---

## 🔄 설정 변경 시나리오

### 빠른 테스트

```bash
# 평소: YAML 설정 사용 (sdxl)
uvicorn src.backend.main:app

# 일회성 테스트: 환경변수로 오버라이드
PRIMARY_MODEL=flux-schnell uvicorn src.backend.main:app

# .env는 그대로 유지!
```

### 영구 변경

**옵션 A: 나만 변경 (권장)**
```bash
# .env 수정
PRIMARY_MODEL=flux-schnell
```

**옵션 B: 팀 전체 변경**
```yaml
# model_config.yaml 수정 후 Git 커밋
runtime:
  primary_model: "flux-schnell"
```

---

## 🎓 환경변수 사용 이유

### 왜 환경변수가 우선일까?

1. **보안**: API 키 같은 민감 정보는 코드/YAML에 넣으면 안됨
2. **유연성**: 배포 환경별로 다른 설정 필요
3. **격리**: 개발자마다 다른 설정 사용 가능
4. **즉시성**: 코드 수정 없이 설정 변경

### 12-Factor App 원칙

현대 애플리케이션 개발의 모범 사례:
> "설정을 환경변수에 저장하라"

https://12factor.net/config

---

## 📋 전체 우선순위 맵

| 설정 항목 | 환경변수 | YAML | 코드 기본값 |
|-----------|----------|------|-------------|
| **모델 선택** | `PRIMARY_MODEL` | `runtime.primary_model` | `"sdxl"` |
| **폴백 활성화** | `ENABLE_FALLBACK` | `runtime.enable_fallback` | `true` |
| **8비트 양자화** | `USE_8BIT` | `runtime.memory.use_8bit` | `false` |
| **API URL** | `API_BASE_URL` | `api.base_url` | `"localhost:8000"` |
| **프롬프트 번역** | `TRANSLATE_KOREAN` | `runtime.prompt_optimization.translate_korean` | `true` |

---

## 🔧 디버깅 팁

### 현재 적용된 설정 확인

```bash
# 백엔드 상태 API 호출
curl http://localhost:8000/status
```

**응답 예시:**
```json
{
  "loaded": true,
  "name": "flux-schnell",  // 실제 로드된 모델
  "device": "cuda"
}
```

### 환경변수 확인

```bash
# 터미널에서
echo $PRIMARY_MODEL

# Python에서
import os
print(os.getenv("PRIMARY_MODEL"))  # None이면 설정 안됨
```

### YAML 설정 확인

```python
from src.backend.model_registry import get_registry

registry = get_registry()
print(registry.get_primary_model())  # 최종 결정된 모델
```

---

## ⚠️ 주의사항

### 함정 1: 환경변수가 적용 안되는 것 같아요

**원인:** 서버가 이미 실행 중
**해결:** 서버 재시작 필수!

```bash
# 백엔드 Ctrl+C 후
uvicorn src.backend.main:app --reload
```

### 함정 2: .env 파일 위치

```
프로젝트/
├── .env          ← 여기 있어야 함!
├── src/
│   ├── backend/
│   │   └── .env  ← ❌ 여기는 안됨
```

### 함정 3: 오타

```bash
# ❌ 틀림
PRIMERY_MODEL=sdxl
PRIAMRY_MODEL=sdxl

# ✅ 맞음
PRIMARY_MODEL=sdxl
```

---

## 🎯 결론

### 언제 뭘 사용할까?

| 상황 | 사용 방법 | 예시 |
|------|-----------|------|
| 팀 기본 설정 | `model_config.yaml` | 모든 개발자가 SDXL 사용 |
| 개인 테스트 | `.env` | 나만 FLUX 테스트 |
| 배포 환경별 | 환경변수 (서버) | dev/staging/prod |
| 임시 테스트 | 명령줄 | `PRIMARY_MODEL=sdxl uvicorn ...` |
| 민감 정보 | `.env` (Git 제외) | API 키, 토큰 |

### 기억하세요!

```
환경변수 > YAML > 코드 기본값
.env가 왕! 👑
```

---

## 📚 관련 문서

- `.env` 설정: `ENV_SETUP_GUIDE.md`
- 모델 설정: `MODEL_SETUP_GUIDE.md`
- 프론트엔드: `FRONTEND_GUIDE.md`
