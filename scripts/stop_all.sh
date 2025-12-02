#!/bin/bash
# 전체 서버 중단 스크립트

PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
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







# #!/bin/bash
# # 전체 서버 중단 스크립트 (개선 버전)

# PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
# LOG_DIR="$PROJECT_ROOT/logs"

# echo "========================================="
# echo "🛑 서비스 중단 (개선 스크립트)"
# echo "========================================="
# echo ""

# # 프로세스 중단 및 확인 함수
# # 인자: $1=서비스 이름, $2=PID 파일 경로, $3=프로세스 검색 패턴
# stop_service() {
#     local SERVICE_NAME=$1
#     local PID_FILE=$2
#     local SEARCH_PATTERN=$3
#     local STATUS_MSG=""
#     local SUCCESS=0

#     echo "▶️ $SERVICE_NAME 중단 시도 중..."

#     # 1. PID 파일을 통한 중단 시도
#     if [ -f "$PID_FILE" ]; then
#         PID=$(cat "$PID_FILE")
#         if ps -p $PID > /dev/null 2>&1; then
#             echo "   [PID 파일 발견] PID $PID를 종료합니다."
#             if kill $PID; then
#                 # 종료 요청 후 프로세스가 실제로 종료되었는지 확인 (최대 5초 대기)
#                 for i in {1..5}; do
#                     if ! ps -p $PID > /dev/null 2>&1; then
#                         STATUS_MSG="✅ $SERVICE_NAME 중단 완료 (PID $PID)"
#                         SUCCESS=1
#                         break
#                     fi
#                     sleep 1
#                 done

#                 if [ $SUCCESS -eq 0 ]; then
#                     STATUS_MSG="⚠️ $SERVICE_NAME (PID $PID) 종료 실패. 수동 확인이 필요합니다."
#                 fi
#             else
#                 STATUS_MSG="❌ $SERVICE_NAME 종료 요청 실패 (kill 명령 실패). PID $PID"
#             fi
#         else
#             STATUS_MSG="⚠️ $SERVICE_NAME 프로세스가 존재하지 않습니다. (PID 파일 삭제)"
#         fi
#         rm -f "$PID_FILE"
#     fi

#     # 2. PID 파일이 없거나 중단에 실패했을 경우, pkill로 중단 시도
#     if [ $SUCCESS -eq 0 ]; then
#         if pgrep -f "$SEARCH_PATTERN" > /dev/null; then
#             echo "   [PID 파일 없음/실패] pkill로 종료를 시도합니다."
#             if pkill -f "$SEARCH_PATTERN"; then
#                 STATUS_MSG="✅ $SERVICE_NAME 중단 요청 성공 (pkill 사용)"
#             else
#                 STATUS_MSG="❌ $SERVICE_NAME 중단 요청 실패 (pkill 권한 오류 또는 명령 실패). 수동 확인 필요."
#             fi
#         else
#             STATUS_MSG="⚠️ 실행 중인 $SERVICE_NAME이 없습니다."
#         fi
#     fi

#     echo "$STATUS_MSG"
#     echo ""
# }

# # 1. Streamlit 중단
# stop_service "Streamlit" "$LOG_DIR/streamlit.pid" "streamlit.*src.frontend.app"

# # 2. Uvicorn 중단
# stop_service "FastAPI (Uvicorn)" "$LOG_DIR/uvicorn.pid" "uvicorn.*src.backend.main:app.*8000"

# # 3. ComfyUI 중단 (외부 스크립트 실행)
# echo "▶️ ComfyUI 중단 중..."
# bash "$PROJECT_ROOT/scripts/stop_comfyui.sh"
# echo "ComfyUI 중단 스크립트 실행 완료."
# echo ""

# echo "========================================="
# echo "✅ 서비스 중단 프로세스 완료!"
# echo "========================================="