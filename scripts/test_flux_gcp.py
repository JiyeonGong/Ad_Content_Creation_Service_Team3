# FLUX 양자화 모델 LoRA 학습 실험용 스크립트

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
import torch
from PIL import Image

# src/backend 모듈 임포트
from src.backend.model_loader import ModelLoader
from src.backend.model_registry import get_registry


def load_test_config(config_path: str) -> dict:
    """테스트 설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def setup_output_dir(base_dir: str) -> Path:
    """출력 디렉토리 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_image(image: Image.Image, output_dir: Path, scenario_name: str, idx: int) -> str:
    """이미지 저장"""
    filename = f"{scenario_name}_{idx:02d}.png"
    filepath = output_dir / filename
    image.save(filepath, format="PNG")
    return str(filepath)


def save_metadata(output_dir: Path, scenario: dict, generation_time: float):
    """메타데이터 저장"""
    metadata = {
        "scenario_name": scenario["name"],
        "prompt": scenario["prompt"],
        "parameters": {
            "width": scenario["width"],
            "height": scenario["height"],
            "steps": scenario["num_inference_steps"],
            "guidance_scale": scenario.get("guidance_scale"),
            "seed": scenario.get("seed"),
        },
        "generation_time_seconds": round(generation_time, 2),
        "description": scenario.get("description", ""),
    }

    metadata_file = output_dir / f"{scenario['name']}_metadata.yaml"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)


def run_scenario(loader: ModelLoader, scenario: dict, output_dir: Path, verbose: bool = True):
    """단일 시나리오 실행"""
    name = scenario["name"]
    print(f"\n{'='*60}")
    print(f"🎨 실험 시작: {name}")
    print(f"{'='*60}")

    if verbose:
        print(f"📝 프롬프트: {scenario['prompt']}")
        print(f"📐 크기: {scenario['width']}x{scenario['height']}")
        print(f"🔢 Steps: {scenario['num_inference_steps']}")
        print(f"🎚️ Guidance: {scenario.get('guidance_scale', 'N/A')}")
        print(f"🌱 Seed: {scenario.get('seed', 'N/A')}")
        print(f"🖼️ 이미지 개수: {scenario['num_images']}")

    start_time = time.time()

    # 이미지 생성 (순차적으로 1개씩)
    images = []
    for i in range(scenario["num_images"]):
        print(f"\n  [{i+1}/{scenario['num_images']}] 생성 중...")

        # 시드 설정
        seed = scenario.get("seed")
        if seed is not None:
            generator = torch.Generator(device=loader.device).manual_seed(seed + i)
        else:
            generator = None

        # 파이프라인 파라미터
        pipeline_params = {
            "prompt": scenario["prompt"],
            "width": scenario["width"],
            "height": scenario["height"],
            "num_inference_steps": scenario["num_inference_steps"],
            "num_images_per_prompt": 1,  # 한 번에 1개씩
            "generator": generator,
        }

        # FLUX는 guidance_scale 선택적
        if scenario.get("guidance_scale") is not None:
            pipeline_params["guidance_scale"] = scenario["guidance_scale"]

        # FLUX max_sequence_length
        if loader.current_model_config.type == "flux":
            pipeline_params["max_sequence_length"] = loader.current_model_config.max_tokens

        # 이미지 생성
        output = loader.t2i_pipe(**pipeline_params)
        images.extend(output.images)

        # 중간 메모리 정리 (마지막 이미지 제외)
        if i < scenario["num_images"] - 1:
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

    generation_time = time.time() - start_time

    # 이미지 저장
    print(f"\n💾 이미지 저장 중...")
    saved_paths = []
    for i, image in enumerate(images):
        path = save_image(image, output_dir, name, i)
        saved_paths.append(path)
        print(f"  ✓ {path}")

    # 메타데이터 저장
    save_metadata(output_dir, scenario, generation_time)

    print(f"\n✅ 완료!")
    print(f"  생성 시간: {generation_time:.2f}초")
    print(f"  평균/이미지: {generation_time/len(images):.2f}초")

    # GPU 메모리 정보 (있으면)
    if torch.cuda.is_available():
        memory_allocated = torch.cuda.memory_allocated() / 1024**3
        memory_reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"  GPU 메모리: {memory_allocated:.2f}GB (할당) / {memory_reserved:.2f}GB (예약)")

    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="GCP VM FLUX 테스트 스크립트")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/test_flux_gcp.yaml",
        help="테스트 설정 파일 경로",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="실행할 특정 시나리오 이름 (없으면 enabled=true인 모든 시나리오)",
    )
    args = parser.parse_args()

    # 설정 로드
    print(f"📂 설정 로드 중: {args.config}")
    config = load_test_config(args.config)

    # 출력 디렉토리 준비
    output_dir = setup_output_dir(config["output"]["base_dir"])
    print(f"📁 출력 디렉토리: {output_dir}")

    # ModelLoader 초기화
    print(f"\n🔧 ModelLoader 초기화 중...")
    model_name = config["model"]["name"]  # "flux-dev" 또는 "flux-dev-gcp"

    # 캐시 디렉토리 (GCP VM에서는 /home/shared 사용)
    cache_dir = str(Path(config["model"]["path"]).parent)

    # bfloat16 사용 여부
    use_bfloat16 = config["memory_optimization"]["dtype"] == "bfloat16"

    loader = ModelLoader(cache_dir=cache_dir, use_bfloat16=use_bfloat16)

    # 모델 로드
    print(f"\n🚀 모델 로딩: {model_name}")

    # 설정에서 지정한 모델명 사용
    success = loader.load_model(model_name)

    if not success:
        print("❌ 모델 로딩 실패")
        sys.exit(1)

    # 테스트 시나리오 실행
    scenarios = config["test_scenarios"]

    # 특정 시나리오만 실행
    if args.scenario:
        scenarios = [s for s in scenarios if s["name"] == args.scenario]
        if not scenarios:
            print(f"❌ 시나리오 '{args.scenario}'를 찾을 수 없습니다.")
            sys.exit(1)
    else:
        # enabled=true인 시나리오만
        scenarios = [s for s in scenarios if s.get("enabled", True)]

    # run_only 필터 적용
    run_only = config["execution"].get("run_only", [])
    if run_only:
        scenarios = [s for s in scenarios if s["name"] in run_only]

    if not scenarios:
        print("❌ 실행할 시나리오가 없습니다.")
        sys.exit(1)

    print(f"\n📋 실행할 시나리오: {len(scenarios)}개")
    for s in scenarios:
        print(f"  - {s['name']}: {s.get('description', '')}")

    # 시나리오 실행
    total_start = time.time()
    results = {}

    for i, scenario in enumerate(scenarios):
        try:
            saved_paths = run_scenario(
                loader,
                scenario,
                output_dir,
                verbose=config["execution"].get("verbose", True)
            )
            results[scenario["name"]] = {
                "status": "success",
                "paths": saved_paths,
            }

            # 다음 실험 전 대기
            if i < len(scenarios) - 1:
                delay = config["execution"].get("delay_between_experiments", 2)
                if delay > 0:
                    print(f"\n⏳ {delay}초 대기 중...")
                    time.sleep(delay)

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

            results[scenario["name"]] = {
                "status": "failed",
                "error": str(e),
            }

            if not config["execution"].get("continue_on_error", True):
                print("❌ continue_on_error=false, 중단합니다.")
                break

    total_time = time.time() - total_start

    # 최종 요약
    print(f"\n{'='*60}")
    print(f"🎉 모든 테스트 완료!")
    print(f"{'='*60}")
    print(f"⏱️ 총 소요 시간: {total_time:.2f}초")
    print(f"\n📊 결과 요약:")

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    failed_count = len(results) - success_count

    print(f"  ✅ 성공: {success_count}개")
    print(f"  ❌ 실패: {failed_count}개")

    print(f"\n📁 출력 디렉토리: {output_dir}")

    # 결과 저장
    results_file = output_dir / "test_results.yaml"
    with open(results_file, 'w', encoding='utf-8') as f:
        yaml.dump({
            "total_time_seconds": round(total_time, 2),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
        }, f, allow_unicode=True, default_flow_style=False)

    print(f"📄 결과 파일: {results_file}")

    # 모델 언로드
    print(f"\n🗑️ 모델 언로드 중...")
    loader.unload_model()

    print(f"\n✨ 완료!")


if __name__ == "__main__":
    main()
