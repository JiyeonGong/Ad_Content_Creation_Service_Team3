#!/bin/bash
# 전체 서버 시작 스크립트 (Uvicorn + ComfyUI + Streamlit)

PROJECT_ROOT="/home/mscho/project3/Ad_Content_Creation_Service_Team3"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

echo "========================================="
echo "💪 헬스케어 AI 콘텐츠 제작 서비스 시작"
echo "========================================="
echo ""

# 1. ComfyUI 시작
echo "1️⃣ ComfyUI 시작 중..."
bash "$PROJECT_ROOT/scripts/start_comfyui.sh"
if [ $? -ne 0 ]; then
    echo "❌ ComfyUI 시작 실패"
    exit 1
fi
echo ""

# ComfyUI 완전 시작 대기
echo "   ComfyUI 초기화 대기 중... (10초)"
sleep 10

# 2. Uvicorn (FastAPI) 시작
echo "2️⃣ FastAPI 백엔드 시작 중..."
cd "$PROJECT_ROOT"

if pgrep -f "uvicorn.*src.backend.main:app.*8000" > /dev/null; then
    echo "⚠️ Uvicorn이 이미 실행 중입니다."
else
    nohup uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/uvicorn.log" 2>&1 &
    UVICORN_PID=$!
    echo $UVICORN_PID > "$LOG_DIR/uvicorn.pid"

    sleep 3

    if pgrep -f "uvicorn.*src.backend.main:app.*8000" > /dev/null; then
        echo "✅ FastAPI 시작 완료! (PID: $UVICORN_PID)"
        echo "   Port: 8000"
        echo "   Log: $LOG_DIR/uvicorn.log"
    else
        echo "❌ FastAPI 시작 실패"
        cat "$LOG_DIR/uvicorn.log"
        exit 1
    fi
fi
echo ""

# 3. Streamlit 시작
echo "3️⃣ Streamlit 프론트엔드 시작 중..."

if pgrep -f "streamlit.*src.frontend.app" > /dev/null; then
    echo "⚠️ Streamlit이 이미 실행 중입니다."
else
    nohup streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0 > "$LOG_DIR/streamlit.log" 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > "$LOG_DIR/streamlit.pid"

    sleep 3

    if pgrep -f "streamlit.*src.frontend.app" > /dev/null; then
        echo "✅ Streamlit 시작 완료! (PID: $STREAMLIT_PID)"
        echo "   Port: 8501"
        echo "   Log: $LOG_DIR/streamlit.log"
    else
        echo "❌ Streamlit 시작 실패"
        cat "$LOG_DIR/streamlit.log"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "✅ 모든 서비스 시작 완료!"
echo "========================================="
echo ""
echo "🌐 접속 정보:"
echo "   - Streamlit UI:   http://localhost:8501"
echo "   - FastAPI Docs:   http://localhost:8000/docs"
echo "   - ComfyUI:        http://localhost:8188"
echo ""
echo "📝 로그 확인:"
echo "   - ComfyUI:   tail -f $LOG_DIR/comfyui.log"
echo "   - FastAPI:   tail -f $LOG_DIR/uvicorn.log"
echo "   - Streamlit: tail -f $LOG_DIR/streamlit.log"
echo ""
echo "🛑 서버 중단: bash scripts/stop_all.sh"
echo ""
