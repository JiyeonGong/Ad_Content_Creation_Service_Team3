#!/bin/bash
# 백엔드 API 집중 모니터링 스크립트
# 이미지 생성/편집 진행 상황, 프로그레스바, 모델 로딩 등을 실시간으로 표시합니다.

PROJECT_ROOT="/home/spai0323/Ad_Content_Creation_Service_Team3"
LOG_DIR="$PROJECT_ROOT/logs"
API_LOG="$LOG_DIR/uvicorn.log"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo "========================================="
echo -e "${CYAN}🚀 백엔드 API 모니터링 시작${NC}"
echo "========================================="
echo -e "${WHITE}모니터링 대상:${NC}"
echo "  📊 이미지 생성/편집 요청"
echo "  📈 진행 상황 (프로그레스)"
echo "  🔄 모델 로딩 상태"
echo "  ⏱️  처리 시간"
echo "  ❌ 에러 및 경고"
echo ""
echo -e "${GRAY}종료하려면 Ctrl+C를 누르세요.${NC}"
echo "========================================="
echo ""

# 로그 파일이 없으면 생성
touch "$API_LOG"

# tail로 로그 실시간 모니터링 + 필터링 및 색상 적용
# --retry: 파일이 사라져도 계속 추적
# -F: 파일이 truncate 되어도 자동으로 다시 열기
tail -F --retry -n 50 "$API_LOG" 2>&1 | while IFS= read -r line; do
    # tail의 특별 메시지 감지 (파일 truncate, 재시작)
    if [[ "$line" == *"truncated"* ]]; then
        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}🔄 [로그 재시작] 백엔드가 재시작되었습니다${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        continue
    fi

    # tail이 파일을 다시 열었다는 메시지 무시
    if [[ "$line" == *"has appeared"* ]] || [[ "$line" == *"has become"* ]]; then
        continue
    fi
    # 타임스탬프 추출
    timestamp=$(echo "$line" | grep -oP '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')

    # 필터링 및 색상 적용
    case "$line" in
        # ========== 이미지 생성 요청 ==========
        *"POST /generate"*)
            echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}📸 [생성 요청]${NC} $line"
            ;;
        *"텍스트→이미지 생성 시작"*)
            echo -e "${CYAN}🎨 [생성 시작]${NC} $line"
            ;;
        *"이미지 생성 완료"*)
            echo -e "${GREEN}✅ [생성 완료]${NC} $line"
            ;;
        *"생성 시간:"*)
            echo -e "${MAGENTA}⏱️  [처리 시간]${NC} $line"
            ;;

        # ========== 이미지 편집 요청 ==========
        *"POST /edit-image"*)
            echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${BLUE}✂️ [편집 요청]${NC} $line"
            ;;
        *"이미지 편집 시작"*)
            echo -e "${CYAN}🎨 [편집 시작]${NC} $line"
            ;;
        *"배경 제거 시작"*)
            echo -e "${YELLOW}🔄 [배경 제거]${NC} $line"
            ;;
        *"편집 완료"*)
            echo -e "${GREEN}✅ [편집 완료]${NC} $line"
            ;;
        *"편집 시간:"*)
            echo -e "${MAGENTA}⏱️  [처리 시간]${NC} $line"
            ;;

        # ========== ComfyUI 상태 ==========
        *"ComfyUI 연결 확인"*)
            echo -e "${GRAY}🔌 [ComfyUI]${NC} $line"
            ;;
        *"큐 등록 성공"*)
            echo -e "${GREEN}📤 [큐 등록]${NC} $line"
            ;;
        *"진행 중"* | *"progress"* | *"Progress"* | *"%"*)
            echo -e "${YELLOW}📊 [진행]${NC} $line"
            ;;

        # ========== 모델 로딩 ==========
        *"모델 로드"* | *"Loading model"* | *"Model loaded"*)
            echo -e "${BLUE}🔄 [모델 로딩]${NC} $line"
            ;;
        *"UNET"* | *"CLIP"* | *"VAE"*)
            echo -e "${BLUE}🧠 [모델]${NC} $line"
            ;;
        *"GGUF"*)
            echo -e "${MAGENTA}📦 [GGUF]${NC} $line"
            ;;

        # ========== 에러 및 경고 ==========
        *"ERROR"* | *"Error"* | *"error"* | *"실패"*)
            echo -e "${RED}❌ [에러]${NC} $line"
            ;;
        *"WARNING"* | *"Warning"* | *"warning"* | *"경고"*)
            echo -e "${YELLOW}⚠️  [경고]${NC} $line"
            ;;
        *"타임아웃"* | *"timeout"* | *"Timeout"*)
            echo -e "${RED}⏱️  [타임아웃]${NC} $line"
            ;;
        *"Connection refused"* | *"연결 거부"*)
            echo -e "${RED}🔌 [연결 실패]${NC} $line"
            ;;

        # ========== HTTP 요청/응답 (상세) ==========
        *"200"* | *"201"*)
            echo -e "${GRAY}✓ [HTTP]${NC} $line"
            ;;
        *"400"* | *"404"* | *"500"*)
            echo -e "${RED}✗ [HTTP]${NC} $line"
            ;;

        # ========== 기타 중요 정보 ==========
        *"POST"* | *"GET"* | *"PUT"* | *"DELETE"*)
            echo -e "${GRAY}→ [API]${NC} $line"
            ;;
        *)
            # 기타 로그는 회색으로 표시 (너무 많으면 주석 처리)
            # echo -e "${GRAY}$line${NC}"
            ;;
    esac
done
