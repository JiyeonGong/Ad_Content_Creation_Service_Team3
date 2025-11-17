# scripts/run_experiment.py
# ============================================================
# 🧪 AI 모델 실험 하네스 스크립트
# - YAML 설정 파일을 읽어 AI 모델(services)을 실행
# - 웹 서버(FastAPI) 없이 모델 단독 실행
# ============================================================

import argparse
import yaml
import os
import sys
from PIL import Image
from io import BytesIO

# -----------------------------------------------------------------
# ⭐️ 중요: src 폴더를 Python 경로에 추가 (uv run이 처리해 주지만, 안전장치)
# -----------------------------------------------------------------
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    # ⭐️ 1. src/backend/services 에서 AI 핵심 로직 import
    from backend import services
except ImportError:
    print(f"오류: 'src' 폴더에서 'backend.services' 모듈을 찾을 수 없습니다.")
    print(f"현재 Python 경로: {sys.path}")
    print("프로젝트 루트에서 'uv run python scripts/run_experiment.py ...'로 실행했는지 확인하세요.")
    sys.exit(1)

# -----------------------------------------------------------------
# 🧪 메인 실행 함수
# -----------------------------------------------------------------
def main(config_path):
    
    # 2. YAML 설정 파일 로드
    print(f"'{config_path}' 설정 파일을 로드합니다.")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"오류: 설정 파일을 찾을 수 없습니다. (경로: {config_path})")
        return
    except Exception as e:
        print(f"오류: YAML 파일 파싱 중 오류 발생: {e}")
        return

    print(f"'{config.get('experiment_name', '이름 없는 실험')}'을(를) 시작합니다.")

    # 3. AI 모델 파이프라인 초기화 (VRAM에 로드)
    # (T2I/I2I 파이프라인 둘 다 로드됨)
    print("AI 모델 파이프라인을 초기화합니다 (SDXL 로딩)...")
    services.init_sdxl_pipelines()
    
    if not services.T2I_PIPE:
        print("오류: SDXL T2I 파이프라인 로딩에 실패했습니다.")
        return

    # 4. T2I 실험 실행 (YAML에서 값 가져오기)
    try:
        print(f"T2I 이미지 생성을 시작합니다... (Steps: {config['steps']})")
        image_bytes = services.generate_t2i_core(
            prompt=config['prompt'],
            width=config['width'],
            height=config['height'],
            steps=config['steps']
            # (참고: negative_prompt, guidance_scale은 services.py 내부 로직을 수정해야 함)
        )
        
        # 5. 결과 저장
        output_path = config['output_path']
        # 출력 폴더가 존재하지 않으면 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
            
        print(f"✅ 실험 완료. 이미지가 '{output_path}'에 저장되었습니다.")

    except Exception as e:
        print(f"❌ T2I 이미지 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 모델 실험 하네스 스크립트")
    parser.add_argument(
        "--config", 
        type=str, 
        required=True, 
        help="실행할 실험의 YAML 설정 파일 경로 (예: configs/experiment_t2i_01.yaml)"
    )
    args = parser.parse_args()
    main(args.config)