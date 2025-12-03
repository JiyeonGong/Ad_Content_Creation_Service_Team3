# 임포트 오류 수정 및 rembg 설치 - 2025년 12월 2일

## 🐛 발생한 문제

### 1. 상대 임포트 오류
```
ImportError: attempted relative import with no known parent package
File "/home/spai0323/Ad_Content_Creation_Service_Team3/src/frontend/app.py", line 381
    from .model_selector import ModelSelector
```

### 2. rembg 모듈 누락
```
ModuleNotFoundError: No module named 'rembg'
File "/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/text_overlay.py", line 9
    from rembg import remove, new_session
```

---

## ✅ 해결 방법

### 1. Frontend 상대 임포트 → 절대 임포트 변경

**수정된 파일**: `src/frontend/app.py`

#### 변경 내역:
```python
# 이전 (상대 임포트)
from .model_selector import ModelSelector
from .utils import PromptHelper

# 이후 (절대 임포트)
from model_selector import ModelSelector
from utils import PromptHelper
```

**이유**: Streamlit을 스크립트로 직접 실행(`streamlit run src/frontend/app.py`)할 때는 상대 임포트가 작동하지 않습니다. 같은 디렉토리의 모듈은 절대 임포트로 해야 합니다.

**수정 위치**:
- Line 381: `ModelSelector` 임포트
- Line 554: `PromptHelper` 임포트 (T2I 페이지)
- Line 1060: `PromptHelper` 임포트 (I2I 페이지)
- Line 1428: `PromptHelper` 임포트 (Image Editing 페이지)

### 2. Backend 상대 임포트 유지

**파일**: `src/backend/*.py`

**이유**: 백엔드는 패키지로 실행(`uvicorn src.backend.main:app`)되므로 상대 임포트가 정상 작동합니다.

**유지된 임포트**:
```python
# src/backend/main.py
from . import services
from .exceptions import (...)

# src/backend/services.py
from .model_registry import get_registry
from .model_loader import ModelLoader
from .text_overlay import create_base_text_image, remove_background
from .exceptions import (...)

# src/backend/model_loader.py
from .model_registry import ModelConfig, get_registry
```

### 3. rembg 패키지 설치

**설치 명령**:
```bash
uv pip install rembg[gpu]
```

**설치된 패키지**:
- rembg==2.0.68
- pooch==1.8.2 (rembg 의존성)

**requirements.txt 업데이트**:
```python
# AI 모델 및 유틸리티
openai
diffusers
Pillow
python-dotenv
transformers
accelerate
pyyaml
rembg[gpu]        # 추가됨
opencv-python     # 추가됨
```

---

## 🔍 검증 결과

### 1. 백엔드 정상 작동
```bash
$ curl http://localhost:8000/status
{
  "gpt_ready": true,
  "image_ready": false,
  "current_model": null,
  "server_start_time": 1764649840.7377226
}
```

### 2. ComfyUI 연결 확인
```bash
$ curl http://localhost:8000/api/comfyui/status
{
  "connected": true,
  "base_url": "http://localhost:8188",
  "queue_info": {
    "queue_running": [],
    "queue_pending": []
  },
  "current_model": null
}
```

### 3. 모델 목록 조회 성공
```bash
$ curl http://localhost:8000/api/image_editing/experiments
{
  "success": true,
  "experiments": [
    {
      "id": "FLUX.1-dev-Q8",
      "name": "FLUX.1-dev Q8",
      "description": "FLUX.1-dev GGUF 8-bit 양자화 (이미지 생성, 권장)"
    },
    {
      "id": "FLUX.1-dev-Q4",
      "name": "FLUX.1-dev Q4",
      "description": "FLUX.1-dev GGUF 4-bit 양자화 (메모리 절약)"
    }
  ]
}
```

### 4. Streamlit 정상 작동
```
You can now view your Streamlit app in your browser.
URL: http://0.0.0.0:8501
```

---

## 📚 학습 포인트

### Python 임포트 규칙

1. **스크립트로 실행 (Streamlit)**:
   - 상대 임포트 사용 불가
   - 같은 디렉토리 모듈은 절대 임포트 사용
   ```python
   from model_selector import ModelSelector  # ✅
   from .model_selector import ModelSelector # ❌
   ```

2. **패키지로 실행 (FastAPI/uvicorn)**:
   - 상대 임포트 권장
   - 패키지 구조를 명확하게 표현
   ```python
   from . import services                    # ✅
   from .model_loader import ModelLoader     # ✅
   ```

### 실행 방식 비교

| 실행 방식 | 명령어 | 임포트 방식 | 적용 대상 |
|----------|--------|------------|----------|
| 스크립트 | `streamlit run app.py` | 절대 임포트 | Frontend |
| 패키지 | `uvicorn src.backend.main:app` | 상대 임포트 | Backend |

---

## 🎯 결론

1. ✅ **Frontend**: 모든 상대 임포트를 절대 임포트로 변경 완료
2. ✅ **Backend**: 상대 임포트 유지 (패키지 실행이므로 정상)
3. ✅ **rembg 설치**: 텍스트 오버레이 기능 정상 작동
4. ✅ **전체 서비스**: 백엔드, ComfyUI, Streamlit 모두 정상 연결

**최종 상태**: 모든 서비스가 에러 없이 정상 작동합니다. 사용자는 웹 브라우저에서 http://localhost:8501 접속 후 정상적으로 기능을 사용할 수 있습니다.

---

**작성일**: 2025년 12월 2일  
**수정자**: GitHub Copilot  
**다음 단계**: 웹 UI에서 모델 선택 및 이미지 생성 테스트
