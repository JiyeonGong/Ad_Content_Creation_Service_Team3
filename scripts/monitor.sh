#!/bin/bash
# 통합 로그 모니터링 스크립트
# ComfyUI, FastAPI(Uvicorn), Streamlit 로그를 동시에 확인합니다.

PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
LOG_DIR="$PROJECT_ROOT/logs"

echo "========================================="
echo "📊 통합 로그 모니터링 시작"
echo "========================================="
echo "모니터링 대상:"
echo "1. ComfyUI: logs/comfyui.log"
echo "2. FastAPI: logs/uvicorn.log"
echo "3. Streamlit: logs/streamlit.log"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo "========================================="

# 로그 파일이 없으면 생성 (tail 에러 방지)
touch "$LOG_DIR/comfyui.log"
touch "$LOG_DIR/uvicorn.log"
touch "$LOG_DIR/streamlit.log"

# tail -f로 모든 로그 동시 출력
# -n 20: 각 파일의 마지막 20줄부터 표시
tail -f -n 20 \
    "$LOG_DIR/comfyui.log" \
    "$LOG_DIR/uvicorn.log" \
    "$LOG_DIR/streamlit.log"
