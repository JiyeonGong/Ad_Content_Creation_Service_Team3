# GCP VM 웹 애플리케이션 실행 가이드

GCP VM에서 Streamlit 웹 애플리케이션을 실행하여 FLUX 모델로 이미지를 생성하는 가이드입니다.

---

## 📋 사전 준비

### 1. GCP VM 환경
- **GPU**: NVIDIA L4 (23GB)
- **CUDA**: 13.0
- **모델 위치**: `/home/shared/FLUX.1-dev`
- **프로젝트**: `~/Ad_Content_Creation_Service_Team3`

### 2. 필요한 설정
- `.env` 파일에 `OPENAI_API_KEY` 설정 필요 (문구 생성 기능용)

---

## 🚀 실행 방법

### Step 1: SSH 접속

```bash
ssh spai0310@lucky-team3
```

### Step 2: 프로젝트 디렉토리로 이동

```bash
cd ~/Ad_Content_Creation_Service_Team3
```

### Step 3: 최신 코드 받기 (mscho 브랜치)

```bash
git fetch origin
git checkout mscho
git pull origin mscho
```

### Step 4: 가상환경 활성화

```bash
source .venv/bin/activate
```

의존성이 업데이트된 경우:
```bash
uv pip install -e .
```

### Step 5: 백엔드 서버 시작 (터미널 1)

```bash
cd ~/Ad_Content_Creation_Service_Team3

# FastAPI 서버 시작 (백그라운드)
uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**중요**: 서버가 시작되면 모델 로딩이 자동으로 진행됩니다 (약 1-2분 소요).

로그에서 다음 메시지를 확인하세요:
```
✅ FastAPI 시작 완료 - 모델 로드됨
```

### Step 6: Streamlit 앱 시작 (터미널 2)

새 터미널을 열고:

```bash
ssh spai0310@lucky-team3
cd ~/Ad_Content_Creation_Service_Team3
source .venv/bin/activate

# Streamlit 앱 시작
uv run streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

### Step 7: 웹 브라우저에서 접속

로컬 머신에서 SSH 터널링 (포트 포워딩):

```bash
# 로컬 터미널에서 실행
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 spai0310@lucky-team3
```

그 다음 브라우저에서:
- **Streamlit**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs

---

## 🖼️ 사용 방법

### 1. 모델 선택

사이드바에서:
1. **이미지 생성 모델** 섹션 확인
2. 현재 모델이 `sdxl` (기본값)로 표시됨
3. 드롭다운에서 **`flux-dev-gcp`** 선택
4. **🔄 모델 전환** 버튼 클릭
5. 로딩 완료 대기 (약 1-2분)

모델 전환 성공 시:
```
✅ 모델 'flux-dev-gcp' 로드 성공
```

### 2. 페이지 1: 홍보 문구 생성

1. 서비스 종류 선택 (예: 요가/필라테스)
2. 지역 입력 (예: 강남)
3. 제품/클래스 이름 입력
4. 핵심 특징 및 장점 입력
5. 톤 선택 (예: 친근한)
6. **✨ 문구+해시태그 생성** 클릭

생성된 문구 중 하나를 선택하면 다음 페이지로 자동 연결됩니다.

### 3. 페이지 2: 이미지 생성 (T2I)

**모델 설정 확인**:
- 현재 모델이 `flux-dev-gcp`인지 확인
- 권장 steps: 28
- 권장 guidance: 3.5

**파라미터 조정**:
- **이미지 크기**: 1024x1024 권장
- **Steps**: 28 (기본값) - 높을수록 정교하지만 느림
- **Guidance Scale**: 3.5 (기본값) - 프롬프트 준수 강도

**생성**:
1. **🖼 3가지 버전 생성** 클릭
2. 약 1-2분 대기 (3개 이미지 생성)
3. 생성된 이미지 확인 및 다운로드

### 4. 페이지 3: 이미지 편집 (I2I)

생성된 이미지를 선택하거나 새 이미지를 업로드하여 편집할 수 있습니다.

---

## ⚙️ 모델별 권장 설정

### FLUX.1-dev (flux-dev-gcp)
```
Steps: 28
Guidance Scale: 3.5
이미지 크기: 1024x1024
예상 시간: 약 30-60초/이미지
메모리: 약 16-18GB
```

**특징**:
- 고품질 이미지 생성
- 한국어 프롬프트 자동 최적화
- 손 디테일 우수
- 텍스트 렌더링 개선

### SDXL (기본 모델)
```
Steps: 30
Guidance Scale: 7.5
이미지 크기: 1024x1024
예상 시간: 약 10-20초/이미지
```

**특징**:
- 빠른 생성 속도
- 안정적
- 인증 불필요

### Playground v2.5
```
Steps: 25
Guidance Scale: 3.0
이미지 크기: 1024x1024
```

**특징**:
- 미적 품질 최적화
- 빠른 속도

---

## 🔧 문제 해결

### 1. 백엔드 연결 실패

**증상**: Streamlit에서 "백엔드 연결 안됨" 표시

**해결**:
```bash
# FastAPI 서버 상태 확인
curl http://localhost:8000/status

# 실행 중이 아니면 재시작
uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

### 2. 모델 로딩 실패

**증상**: `❌ 모델 'flux-dev-gcp' 로드 실패`

**해결**:
```bash
# 모델 경로 확인
ls -la /home/shared/FLUX.1-dev

# 없으면 test_flux_gcp.py로 먼저 테스트
uv run python scripts/test_flux_gcp.py --scenario exp01_basic_test
```

### 3. GPU 메모리 부족

**증상**: "GPU 메모리 부족" 에러

**해결**:
1. 이미지 크기를 줄이기 (1024 → 512)
2. 다른 모델로 전환 (sdxl 또는 playground)
3. 백엔드 서버 재시작

```bash
# GPU 메모리 확인
nvidia-smi

# 서버 재시작
pkill -f uvicorn
uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

### 4. OPENAI_API_KEY 에러

**증상**: "OpenAI 클라이언트가 초기화되지 않았습니다"

**해결**:
```bash
# .env 파일 확인
cat .env | grep OPENAI_API_KEY

# 없으면 추가
echo "OPENAI_API_KEY=your_key_here" >> .env

# 서버 재시작
```

### 5. 포트 충돌

**증상**: `Address already in use: 8000` 또는 `8501`

**해결**:
```bash
# 포트 사용 중인 프로세스 확인 및 종료
lsof -ti:8000 | xargs kill -9
lsof -ti:8501 | xargs kill -9
```

---

## 📊 성능 비교

### GCP VM (L4 GPU)
- **FLUX-dev**: 30-60초/이미지 (steps=28)
- **SDXL**: 10-20초/이미지 (steps=30)

### 로컬 (RTX 5060 Ti)
- **FLUX-dev**: 15-30초/이미지 (더 빠름)
- **SDXL**: 5-10초/이미지

> **참고**: L4 GPU는 메모리는 더 많지만 (23GB), RTX 5060 Ti보다 연산 성능이 낮습니다.

---

## 💡 팁

### 1. 연결 모드 활용
- 사이드바의 **🔗 페이지 연결 모드** 활성화
- 페이지 1에서 문구 생성 → 페이지 2에서 이미지 생성
- 데이터가 자동으로 연결됨

### 2. 모델 전환 시기
- **고품질 필요**: `flux-dev-gcp` (느리지만 고품질)
- **빠른 테스트**: `sdxl` 또는 `playground`
- **미적 감각**: `playground`

### 3. Guidance Scale 조정
- **낮음 (2.0-3.0)**: 더 창의적, 자유로운 해석
- **중간 (3.5-5.0)**: 균형잡힌 (권장)
- **높음 (7.0-10.0)**: 프롬프트 엄격 준수

### 4. 백그라운드 실행
서버를 백그라운드로 실행하려면:

```bash
# nohup으로 실행
nohup uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
nohup uv run streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &

# 로그 확인
tail -f backend.log
tail -f streamlit.log
```

---

## 📝 참고

- 이 웹 애플리케이션은 `scripts/test_flux_gcp.py`와 동일한 model_loader를 사용합니다
- ai-ad 프로젝트의 메모리 최적화 기법 적용됨
- 모델별 권장 파라미터가 자동으로 표시됨
- 한국어 프롬프트는 자동으로 영어로 최적화됨

## 🔗 관련 문서

- [GCP_VM_SETUP.md](./GCP_VM_SETUP.md) - 초기 설정 및 테스트 스크립트
- [model_config.yaml](../src/backend/model_config.yaml) - 모델 설정
- [test_flux_gcp.yaml](../configs/test_flux_gcp.yaml) - 테스트 시나리오
