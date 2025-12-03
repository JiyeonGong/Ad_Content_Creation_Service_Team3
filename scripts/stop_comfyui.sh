#!/bin/bash
# ComfyUI 중단 스크립트

PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
PID_FILE="$PROJECT_ROOT/logs/comfyui.pid"

echo "========================================="
echo "ComfyUI 중단"
echo "========================================="

# PID 파일에서 읽기
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 ComfyUI 프로세스 종료 중... (PID: $PID)"
        kill $PID
        sleep 2

        # 강제 종료 확인
        if ps -p $PID > /dev/null 2>&1; then
            echo "   강제 종료 중..."
            kill -9 $PID
        fi

        rm -f "$PID_FILE"
        echo "✅ ComfyUI 중단 완료"
    else
        echo "⚠️ PID $PID 프로세스가 존재하지 않습니다."
        rm -f "$PID_FILE"
    fi
else
    # PID 파일이 없으면 프로세스 검색
    if pgrep -f "python.*main.py.*8188" > /dev/null; then
        echo "🛑 ComfyUI 프로세스 종료 중..."
        pkill -f "python.*main.py.*8188"
        sleep 2
        echo "✅ ComfyUI 중단 완료"
    else
        echo "⚠️ 실행 중인 ComfyUI가 없습니다."
    fi
fi
