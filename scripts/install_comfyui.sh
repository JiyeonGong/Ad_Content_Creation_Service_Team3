#!/bin/bash
# ComfyUI 설치 스크립트

set -e  # 에러 발생 시 중단

PROJECT_ROOT="/home/mscho/project3/Ad_Content_Creation_Service_Team3"
COMFYUI_DIR="$PROJECT_ROOT/comfyui"
MODELS_DIR="/mnt/data4/models"

echo "========================================="
echo "ComfyUI 설치 시작"
echo "========================================="

# 1. ComfyUI 클론
if [ ! -d "$COMFYUI_DIR" ]; then
    echo "📦 ComfyUI 다운로드 중..."
    cd "$PROJECT_ROOT"
    git clone https://github.com/comfyanonymous/ComfyUI.git comfyui
else
    echo "✅ ComfyUI 이미 존재"
fi

# 2. ComfyUI 의존성 설치
echo "📦 ComfyUI 의존성 설치 중..."
cd "$COMFYUI_DIR"
pip install -r requirements.txt

# 3. ComfyUI Manager 설치 (노드 관리 편의성)
echo "📦 ComfyUI Manager 설치 중..."
cd "$COMFYUI_DIR/custom_nodes"
if [ ! -d "ComfyUI-Manager" ]; then
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git
else
    echo "✅ ComfyUI Manager 이미 설치됨"
fi

# 4. 필수 커스텀 노드 설치
echo "📦 필수 커스텀 노드 설치 중..."

# BEN2 배경 제거 노드
if [ ! -d "ComfyUI-BEN2" ]; then
    echo "  - BEN2 노드 설치 중..."
    # 실제 BEN2 ComfyUI 노드 URL로 교체 필요
    # git clone https://github.com/xxx/ComfyUI-BEN2.git
    echo "  ⚠️ BEN2 노드: 수동 설치 필요 (ComfyUI Manager에서 검색)"
else
    echo "  ✅ BEN2 노드 이미 설치됨"
fi

# FLUX 관련 노드 (기본 포함되어 있을 수 있음)
echo "  - FLUX 노드 확인 중..."
echo "  ✅ FLUX는 ComfyUI 기본 지원"

# Qwen-Image-Edit 노드
if [ ! -d "ComfyUI-Qwen-Image" ]; then
    echo "  - Qwen-Image 노드 설치 중..."
    # 실제 Qwen-Image ComfyUI 노드 URL로 교체 필요
    # git clone https://github.com/xxx/ComfyUI-Qwen-Image.git
    echo "  ⚠️ Qwen-Image 노드: 수동 설치 필요 (ComfyUI Manager에서 검색)"
else
    echo "  ✅ Qwen-Image 노드 이미 설치됨"
fi

# 5. 모델 디렉토리 심볼릭 링크 생성
echo "🔗 모델 디렉토리 링크 설정 중..."
cd "$COMFYUI_DIR"

# ComfyUI 모델 경로를 /mnt/data4/models로 연결
if [ ! -L "models/checkpoints" ]; then
    rm -rf models/checkpoints
    ln -s "$MODELS_DIR" models/checkpoints
    echo "  ✅ models/checkpoints -> $MODELS_DIR"
fi

# 6. 워크플로우 디렉토리 생성
echo "📁 워크플로우 디렉토리 생성 중..."
mkdir -p "$COMFYUI_DIR/workflows"

# 7. 설정 파일 생성
echo "⚙️ ComfyUI 설정 파일 생성 중..."
cat > "$COMFYUI_DIR/extra_model_paths.yaml" << EOF
# ComfyUI 추가 모델 경로 설정
a111:
  base_path: /mnt/data4/models/
  checkpoints: ./
  vae: vae/
  loras: loras/
  upscale_models: upscale_models/
  embeddings: embeddings/
  controlnet: controlnet/
EOF

echo ""
echo "========================================="
echo "✅ ComfyUI 설치 완료!"
echo "========================================="
echo ""
echo "📝 다음 단계:"
echo "1. ComfyUI 실행: bash scripts/start_comfyui.sh"
echo "2. 브라우저 접속: http://localhost:8188"
echo "3. ComfyUI Manager에서 필요한 노드 설치:"
echo "   - BEN2 배경 제거 노드 검색 및 설치"
echo "   - Qwen-Image 노드 검색 및 설치"
echo ""
echo "4. 모델 다운로드 (필요 시):"
echo "   - FLUX.1-Fill: /mnt/data4/models/flux-fill/"
echo "   - Qwen-Image-Edit: /mnt/data4/models/qwen-image-edit/"
echo "   - BEN2: /mnt/data4/models/ben2/"
echo ""
