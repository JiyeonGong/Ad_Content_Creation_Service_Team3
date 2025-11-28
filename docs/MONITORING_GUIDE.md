# 📊 백엔드 모니터링 가이드

## 개요

백엔드 API의 이미지 생성/편집 작업을 실시간으로 모니터링하는 전용 스크립트입니다.

## 🎯 주요 기능

### 실시간 모니터링 항목

- ✅ **이미지 생성 요청** - Text-to-Image 작업 추적
- ✅ **이미지 편집 요청** - 배경 제거 + 편집 작업 추적
- ✅ **진행 상황** - 실시간 프로그레스 표시
- ✅ **모델 로딩** - GGUF/FLUX/CLIP/VAE 로딩 상태
- ✅ **처리 시간** - 각 단계별 소요 시간 측정
- ✅ **ComfyUI 연결** - 큐 등록 및 작업 상태
- ✅ **에러 및 경고** - 문제 발생 시 즉시 표시

### 색상 구분

- 🟢 **초록색** - 성공, 완료
- 🔵 **파란색** - 편집 작업, 모델 로딩
- 🟡 **노란색** - 진행 중, 경고
- 🔴 **빨간색** - 에러, 실패
- ⚪ **흰색** - 요청 시작
- ⚫ **회색** - 일반 로그

## 🚀 사용법

### 기본 실행

```bash
bash scripts/monitor_backend.sh
```

### 백그라운드 실행

```bash
nohup bash scripts/monitor_backend.sh > logs/monitor.log 2>&1 &
```

### 종료

```
Ctrl + C
```

## 📝 출력 예시

### 이미지 생성 작업

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 [생성 요청] POST /generate
🎨 [생성 시작] 텍스트→이미지 생성 시작
   실험: FLUX.1-Dev
   모델: ['FLUX.1-dev']
   프롬프트: A professional gym trainer...
   파라미터: steps=28, guidance=3.5, strength=1.0
🔄 [워크플로우] 실행 중...
📤 [이미지] 업로드 중... (크기: 245.3KB)
✅ [업로드] 완료: input.png
✅ [큐 등록] 워크플로우 큐 등록: abc123-def456
⏳ [작업] 시작 (ID: abc123-def456)
📊 [진행 중] ... 5초 경과
📊 [진행 중] ... 10초 경과
✅ [작업] 완료! (소요 시간: 15.3초)
📥 [출력] 이미지 다운로드 중... (1개 노드)
   ✓ flux_output_001.png (512.7KB)
✅ [출력] 이미지 1개 추출 완료
✅ [생성 완료] 소요 시간: 16.2초
⏱️  [처리 시간] 16.2초
```

### 이미지 편집 작업

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✂️ [편집 요청] POST /edit-image
🎨 [편집 시작] 이미지 편집 시작
   실험: BEN2 + FLUX.1-Fill
   모델: ['BEN2', 'FLUX.1-Fill']
   프롬프트: beach sunset background
   파라미터: steps=28, guidance=3.5, strength=1.0
🔄 [워크플로우] 실행 중...
📤 [이미지] 업로드 중... (크기: 387.2KB)
✅ [업로드] 완료: input.png
🔄 [배경 제거] BEN2 처리 중...
🧠 [모델] FLUX.1-Fill UNET 로딩...
🧠 [모델] CLIP 로딩...
🧠 [모델] VAE 로딩...
📊 [진행 중] ... 8초 경과
📊 [진행 중] ... 16초 경과
✅ [작업] 완료! (소요 시간: 22.7초)
📥 [출력] 이미지 다운로드 중... (2개 노드)
   ✓ ben2_output_001.png (423.1KB)
   ✓ flux_fill_output_001.png (856.4KB)
✅ [출력] 이미지 2개 추출 완료
✅ [편집 완료] 소요 시간: 23.5초
⏱️  [처리 시간] 23.5초
```

### 에러 발생 시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✂️ [편집 요청] POST /edit-image
🎨 [편집 시작] 이미지 편집 시작
❌ [에러] ComfyUI 연결 실패
🔌 [연결 실패] Connection refused
⚠️  [경고] ComfyUI가 실행 중인지 확인하세요
⏱️  [타임아웃] 작업 타임아웃 (300초 초과)
```

## 📋 필터링 규칙

스크립트는 다음 키워드를 감지하여 자동으로 필터링하고 색상을 적용합니다:

### 생성/편집 요청
- `POST /generate` - 생성 요청
- `POST /edit-image` - 편집 요청
- `텍스트→이미지`, `이미지 생성`, `이미지 편집`

### 진행 상황
- `시작`, `완료`, `진행 중`, `progress`, `Progress`
- `큐 등록`, `작업 진행`

### 모델 관련
- `모델 로드`, `Loading model`, `Model loaded`
- `UNET`, `CLIP`, `VAE`, `GGUF`
- `배경 제거`

### 처리 시간
- `생성 시간`, `편집 시간`, `처리 시간`, `소요 시간`

### 에러 및 경고
- `ERROR`, `Error`, `error`, `실패`
- `WARNING`, `Warning`, `warning`, `경고`
- `타임아웃`, `timeout`, `Timeout`
- `Connection refused`, `연결 거부`

### HTTP 상태
- `200`, `201` - 성공
- `400`, `404`, `500` - 에러

## 🔧 커스터마이징

### 로그 파일 변경

스크립트 내 `API_LOG` 변수를 수정:

```bash
API_LOG="$LOG_DIR/api.log"  # 기본값
```

### 필터링 규칙 추가

`case "$line" in` 섹션에 새로운 패턴 추가:

```bash
*"새로운 키워드"*)
    echo -e "${COLOR}[라벨] $line"
    ;;
```

### 색상 변경

스크립트 상단의 색상 코드 수정:

```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
```

## 📌 참고사항

### 로그 위치

- **API 로그**: `logs/api.log`
- **ComfyUI 로그**: `logs/comfyui.log`
- **Streamlit 로그**: `logs/streamlit.log`

### 전체 로그 확인

모든 서비스 로그를 함께 보려면 기존 스크립트 사용:

```bash
bash scripts/monitor.sh
```

### 로그 레벨 조정

더 상세한 로그를 보려면 FastAPI 실행 시 로그 레벨 변경:

```bash
uvicorn src.backend.main:app --log-level debug
```

## 🐛 문제 해결

### 로그가 표시되지 않음

```bash
# API 로그 파일 존재 확인
ls -lh logs/api.log

# FastAPI 실행 확인
ps aux | grep uvicorn

# 로그 파일 직접 확인
tail -f logs/api.log
```

### 색상이 표시되지 않음

터미널이 ANSI 색상을 지원하는지 확인:

```bash
echo -e "\033[0;32mGreen\033[0m"
```

### 권한 에러

실행 권한 부여:

```bash
chmod +x scripts/monitor_backend.sh
```

## 💡 팁

### 1. 여러 터미널 사용

```bash
# 터미널 1: 백엔드 모니터링
bash scripts/monitor_backend.sh

# 터미널 2: ComfyUI 로그
tail -f logs/comfyui.log

# 터미널 3: 서비스 실행
```

### 2. 특정 키워드만 필터링

```bash
tail -f logs/api.log | grep "편집"
```

### 3. 로그 저장

```bash
bash scripts/monitor_backend.sh | tee logs/monitor_output.log
```

### 4. 실시간 통계

```bash
# 성공/실패 카운트
tail -f logs/api.log | grep -E "(성공|실패)" | wc -l
```

## 📚 관련 문서

- [ComfyUI 통합 가이드](./COMFYUI_INTEGRATION.md)
- [이미지 편집 가이드](./IMAGE_EDITING_GUIDE.md)
- [환경 설정 가이드](./env_setup_guide.md)
