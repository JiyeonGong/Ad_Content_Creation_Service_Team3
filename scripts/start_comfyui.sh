#!/bin/bash
# ComfyUI 백그라운드 실행 스크립트

PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
COMFYUI_DIR="$PROJECT_ROOT/comfyui"
LOG_FILE="$PROJECT_ROOT/logs/comfyui.log"

# 로그 디렉토리 생성
mkdir -p "$PROJECT_ROOT/logs"

echo "========================================="
echo "ComfyUI 시작"
echo "========================================="

# 이미 실행 중인지 확인
if pgrep -f "python.*main.py.*8188" > /dev/null; then
    echo "⚠️ ComfyUI가 이미 실행 중입니다."
    echo "   중단하려면: bash scripts/stop_comfyui.sh"
    exit 0
fi

# ComfyUI 디렉토리 확인
if [ ! -d "$COMFYUI_DIR" ]; then
    echo "❌ ComfyUI가 설치되지 않았습니다."
    echo "   먼저 설치하세요: bash scripts/install_comfyui.sh"
    exit 1
fi

# ComfyUI 실행
cd "$COMFYUI_DIR"
echo "🚀 ComfyUI 백그라운드 실행 중..."
echo "   Port: 8188"
echo "   Log: $LOG_FILE"

# 프로젝트 가상환경의 Python 사용
nohup "$PROJECT_ROOT/.venv/bin/python" main.py --listen 0.0.0.0 --port 8188 > "$LOG_FILE" 2>&1 &

# PID 저장
COMFYUI_PID=$!
echo $COMFYUI_PID > "$PROJECT_ROOT/logs/comfyui.pid"

# 시작 대기
sleep 3

# 실행 확인
if pgrep -f "python.*main.py.*8188" > /dev/null; then
    echo "✅ ComfyUI 시작 완료!"
    echo "   PID: $COMFYUI_PID"
    echo "   접속: http://localhost:8188"
    echo ""
    echo "📝 로그 확인: tail -f $LOG_FILE"
else
    echo "❌ ComfyUI 시작 실패"
    echo "   로그 확인: cat $LOG_FILE"
    exit 1
fi
