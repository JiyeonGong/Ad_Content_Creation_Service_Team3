#!/bin/bash
# 전체 서버 중단 스크립트

PROJECT_ROOT="/home/mscho/project3/Ad_Content_Creation_Service_Team3"
LOG_DIR="$PROJECT_ROOT/logs"

echo "========================================="
echo "🛑 서비스 중단"
echo "========================================="
echo ""

# 1. Streamlit 중단
echo "1️⃣ Streamlit 중단 중..."
if [ -f "$LOG_DIR/streamlit.pid" ]; then
    PID=$(cat "$LOG_DIR/streamlit.pid")
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        rm -f "$LOG_DIR/streamlit.pid"
        echo "✅ Streamlit 중단 완료"
    else
        echo "⚠️ Streamlit 프로세스가 존재하지 않습니다."
        rm -f "$LOG_DIR/streamlit.pid"
    fi
elif pgrep -f "streamlit.*src.frontend.app" > /dev/null; then
    pkill -f "streamlit.*src.frontend.app"
    echo "✅ Streamlit 중단 완료"
else
    echo "⚠️ 실행 중인 Streamlit이 없습니다."
fi
echo ""

# 2. Uvicorn 중단
echo "2️⃣ FastAPI 중단 중..."
if [ -f "$LOG_DIR/uvicorn.pid" ]; then
    PID=$(cat "$LOG_DIR/uvicorn.pid")
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        rm -f "$LOG_DIR/uvicorn.pid"
        echo "✅ FastAPI 중단 완료"
    else
        echo "⚠️ FastAPI 프로세스가 존재하지 않습니다."
        rm -f "$LOG_DIR/uvicorn.pid"
    fi
elif pgrep -f "uvicorn.*src.backend.main:app.*8000" > /dev/null; then
    pkill -f "uvicorn.*src.backend.main:app.*8000"
    echo "✅ FastAPI 중단 완료"
else
    echo "⚠️ 실행 중인 FastAPI가 없습니다."
fi
echo ""

# 3. ComfyUI 중단
echo "3️⃣ ComfyUI 중단 중..."
bash "$PROJECT_ROOT/scripts/stop_comfyui.sh"
echo ""

echo "========================================="
echo "✅ 모든 서비스 중단 완료!"
echo "========================================="
