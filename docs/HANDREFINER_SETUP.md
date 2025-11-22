# HandRefiner 설치 가이드

> 2025-11-22 작성
> MeshGraphormer 기반 3D 손 메시 재구성으로 **손가락 정확히 5개를 보장**하는 후처리 도구

---

## 📋 요약

| 항목 | 값 |
|------|-----|
| 목적 | AI 이미지 생성 시 손가락 개수 오류 보정 |
| 기술 | MeshGraphormer + ControlNet Inpainting |
| GPU 메모리 | 추가 ~3GB 필요 |
| 처리 시간 | 이미지당 10-20초 추가 |

---

## 1. Python 패키지 설치

### 1.1. handrefiner 기본 의존성 설치

```bash
# handrefiner 선택적 의존성 설치
uv pip install -e ".[handrefiner]"
```

### 1.2. 수동 설치 필요한 패키지

**⚠️ 중요**: `manopth`와 `chumpy`는 일부 플랫폼에서 PyPI 미지원 또는 빌드 문제가 있어 **수동 설치**가 필요합니다.

```bash
# manopth 수동 설치
uv pip install manopth

# chumpy 수동 설치 (빌드 시 pip 필요)
uv pip install pip  # chumpy 빌드를 위해 필요
uv pip install --no-build-isolation chumpy

# rtree (메시 공간 인덱싱)
uv pip install rtree

# timm (HRNet 가중치 다운로드용)
uv pip install timm
```

---

## 2. HandRefiner 저장소 클론

```bash
# 프로젝트 루트에서 실행
mkdir -p models
cd models

# HandRefiner 저장소 클론
git clone https://github.com/wenquanlu/HandRefiner.git handrefiner
cd handrefiner

# HandRefiner 자체 의존성 설치 (선택)
pip install -r requirements.txt
```

---

## 3. MeshGraphormer 설치

```bash
cd models/handrefiner
git clone --recursive https://github.com/microsoft/MeshGraphormer.git
```

---

## 4. Python 3.12 호환성 패치

**중요**: HandRefiner와 MeshGraphormer는 Python 3.8-3.10용으로 작성되어 Python 3.12에서 호환성 문제가 있습니다.

### 4.1. PyTorch Lightning 패치

```bash
# models/handrefiner/ldm/models/diffusion/ddpm.py (20번 라인)
# models/handrefiner/cldm/logger.py (8번 라인)
# 아래 코드로 수정:
try:
    from pytorch_lightning.utilities.distributed import rank_zero_only
except ImportError:
    from pytorch_lightning.utilities.rank_zero import rank_zero_only
```

### 4.2. chumpy numpy 호환성 패치

```bash
# .venv/lib/python3.12/site-packages/chumpy/__init__.py 수정:
# 기존: from numpy import bool, int, float, complex, object, unicode, str, nan, inf
# 수정:
from numpy import nan, inf
bool, int, float, complex, object, str = bool, int, float, complex, object, str

# .venv/lib/python3.12/site-packages/chumpy/ch.py 수정:
# 모든 inspect.getargspec를 inspect.getfullargspec로 변경
sed -i 's/inspect\.getargspec/inspect.getfullargspec/g' .venv/lib/python3.12/site-packages/chumpy/ch.py
```

### 4.3. MeshGraphormer 경로 수정

MeshGraphormer는 상대 경로를 하드코딩하고 있어 절대 경로로 수정이 필요합니다.

**models/handrefiner/MeshGraphormer/src/modeling/data/config.py:**
```python
from os.path import join, dirname, abspath
import os

# Get absolute path to this config file's directory
config_dir = dirname(abspath(__file__))
folder_path = config_dir + '/'

MANO_FILE = folder_path + 'MANO_RIGHT.pkl'
MANO_sampling_matrix = folder_path + 'mano_downsampling.npz'
# ... 나머지 경로들도 folder_path 기준으로 수정
```

### 4.4. MeshGraphormer Import 수정

```bash
cd models/handrefiner/MeshGraphormer

# modeling_graphormer.py 수정
sed -i 's|import src.modeling.data.config as cfg|from ..data import config as cfg|g' \
  src/modeling/bert/modeling_graphormer.py
sed -i 's|from src.modeling._gcnn import|from .._gcnn import|g' \
  src/modeling/bert/modeling_graphormer.py

# _mano.py 수정
sed -i 's|import src.modeling.data.config as cfg|from .data import config as cfg|g' \
  src/modeling/_mano.py

# _smpl.py 수정
sed -i 's|from src.utils.geometric_layers import|from ..utils.geometric_layers import|g' \
  src/modeling/_smpl.py
sed -i 's|import src.modeling.data.config as cfg|from .data import config as cfg|g' \
  src/modeling/_smpl.py

# e2e network 파일들 수정
sed -i 's|import src.modeling.data.config as cfg|from ..data import config as cfg|g' \
  src/modeling/bert/e2e_hand_network.py
sed -i 's|import src.modeling.data.config as cfg|from ..data import config as cfg|g' \
  src/modeling/bert/e2e_body_network.py
```

---

## 5. 모델 가중치 다운로드

### 5.1. MANO 모델 다운로드

```bash
# HuggingFace 미러에서 다운로드
wget -O models/handrefiner/MeshGraphormer/src/modeling/data/MANO_RIGHT.pkl \
  https://huggingface.co/camenduru/HandRefiner/resolve/main/MANO_RIGHT.pkl
```

### 5.2. MeshGraphormer 가중치

```bash
# 디렉토리 생성
mkdir -p models/handrefiner/MeshGraphormer/models/graphormer_release

# HuggingFace에서 다운로드 (816 MB)
wget -O models/handrefiner/MeshGraphormer/models/graphormer_release/graphormer_hand_state_dict.bin \
  https://huggingface.co/camenduru/HandRefiner/resolve/main/graphormer_hand_state_dict.bin
```

### 5.3. HRNet 가중치

```bash
# timm을 통한 자동 다운로드 (권장)
uv run python -c "
import timm
import torch
from pathlib import Path

hrnet_dir = Path('models/handrefiner/MeshGraphormer/models/hrnet')
hrnet_dir.mkdir(parents=True, exist_ok=True)

print('Loading HRNet-W64 from timm...')
model = timm.create_model('hrnet_w64', pretrained=True)
torch.save(model.state_dict(), hrnet_dir / 'hrnetv2_w64_imagenet_pretrained.pth')
print('HRNet weights saved! (489.7 MB)')
"
```

### 5.4. HRNet Config 다운로드

```bash
curl -L "https://raw.githubusercontent.com/HRNet/HRNet-Image-Classification/master/experiments/cls_hrnet_w64_sgd_lr5e-2_wd1e-4_bs32_x100.yaml" \
  -o models/handrefiner/MeshGraphormer/models/hrnet/cls_hrnet_w64_sgd_lr5e-2_wd1e-4_bs32_x100.yaml
```

### 5.5. MediaPipe Hand Landmarker

```bash
mkdir -p preprocessor
curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" \
  -o preprocessor/hand_landmarker.task
```

### 5.6. HandRefiner ControlNet 가중치

```bash
cd models/handrefiner

# HuggingFace에서 다운로드 (8.6 GB)
wget https://huggingface.co/hr16/ControlNet-HandRefiner-pruned/resolve/main/inpaint_depth_control.ckpt
```

---

## 6. 설정 파일 수정

### 6.1. model_config.yaml

`src/backend/model_config.yaml`에서 HandRefiner 활성화:

```yaml
runtime:
  # ... 기존 설정 ...

  handrefiner:
    enable: true  # false → true로 변경
    model_path: "models/handrefiner"
    weights_path: "models/handrefiner/inpaint_depth_control.ckpt"
    control_strength: 0.6  # 0.4-0.8 권장
    inpaint_steps: 20
```

---

## 7. 설치 확인

```bash
uv run python -c "
import sys
sys.path.insert(0, 'src/backend')

from handrefiner_wrapper import HandRefinerWrapper

config = {
    'enable': True,
    'model_path': 'models/handrefiner',
    'weights_path': 'models/handrefiner/inpaint_depth_control.ckpt',
    'control_strength': 0.6,
    'inpaint_steps': 20
}

wrapper = HandRefinerWrapper(config)
if wrapper.load_handrefiner():
    print('✅ HandRefiner 설치 성공!')
    print(f'✅ ControlNet: {wrapper.inpaint_model is not None}')
    print(f'✅ MeshGraphormer: {wrapper.mesh_graphormer is not None}')
else:
    print('❌ HandRefiner 설치 실패')
"
```

---

## 8. 다운로드 파일 요약

설치 완료 후 다음 파일들이 존재해야 합니다:

```
models/handrefiner/
├── inpaint_depth_control.ckpt (8.6 GB)
├── MeshGraphormer/
│   ├── src/modeling/data/
│   │   └── MANO_RIGHT.pkl (3.7 MB)
│   └── models/
│       ├── graphormer_release/
│       │   └── graphormer_hand_state_dict.bin (816 MB)
│       └── hrnet/
│           ├── hrnetv2_w64_imagenet_pretrained.pth (489.7 MB)
│           └── cls_hrnet_w64_sgd_lr5e-2_wd1e-4_bs32_x100.yaml (1.4 KB)
```

**총 용량**: 약 10GB

---

## 9. 트러블슈팅

### 문제 1: `No module named 'pytorch_lightning.utilities.distributed'`
- **원인**: PyTorch Lightning 2.x에서 모듈 경로 변경
- **해결**: 섹션 4.1의 패치 적용

### 문제 2: `cannot import name 'bool' from 'numpy'`
- **원인**: numpy 1.20+에서 deprecated된 타입 알리아스 제거
- **해결**: 섹션 4.2의 chumpy 패치 적용

### 문제 3: `module 'inspect' has no attribute 'getargspec'`
- **원인**: Python 3.11+에서 `getargspec` 제거됨
- **해결**: 섹션 4.2의 chumpy sed 명령 실행

### 문제 4: `FileNotFoundError: MANO_RIGHT.pkl`
- **원인**: 상대 경로 하드코딩
- **해결**: 섹션 4.3의 경로 수정 적용

### 문제 5: CUDA out of memory
- **원인**: HandRefiner가 추가 GPU 메모리 필요 (~3GB)
- **해결**:
  - `model_config.yaml`에서 `handrefiner.enable: false`로 비활성화
  - 또는 배치 크기를 줄이고 순차 처리

### 문제 6: xformers GPU compatibility 에러
- **원인**: xformers의 FlashAttention이 GPU capability 12.0 미지원
- **해결**: PyTorch SDPA 사용으로 변경 (models/handrefiner/ldm/modules/diffusionmodules/model.py 수정)

---

## 10. 참고 자료

- [HandRefiner GitHub](https://github.com/wenquanlu/HandRefiner)
- [MeshGraphormer GitHub](https://github.com/microsoft/MeshGraphormer)
- [MANO 공식 사이트](https://mano.is.tue.mpg.de/)
- [ControlNet-HandRefiner-pruned (HuggingFace)](https://huggingface.co/hr16/ControlNet-HandRefiner-pruned)
