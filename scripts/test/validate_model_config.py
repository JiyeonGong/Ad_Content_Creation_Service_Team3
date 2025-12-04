# /home/spai0323/Ad_Content_Creation_Service_Team3/test/validate_model_config.py
import os
import yaml

# 절대 경로를 문자열로 정의 (프로젝트 루트가 고정되어 있을 경우)
PROJECT_ROOT = "/home/spai0323/Ad_Content_Creation_Service_Team3"

# os.path.join()을 사용하여 경로 결합
CONFIG_PATH = os.path.join(
    PROJECT_ROOT,
    "configs",
    "model_config.yaml"
)

REQUIRED_MODEL_FIELDS = ["id", "type", "params", "description"]

# params 내에서 권장은 아니더라도 registry.ModelConfig가 사용하는 필드들
REQUIRED_PARAMS = [
    "default_steps",
    "max_steps",
    "use_negative_prompt",
    "guidance_scale",
    "supports_i2i",
    "max_tokens",
    "default_size",
    "max_size"
]

def validate_model_config():
    print("🔍 model_config.yaml 검증 시작\n")

    if not os.path.exists(CONFIG_PATH):
        print(f"❌ 파일을 찾을 수 없음: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ YAML 파싱 실패: {e}")
            return

    errors = []

    # -------------------------------
    # 1) models 루트 키 검사
    # -------------------------------
    models = config.get("models")
    if not isinstance(models, dict):
        errors.append("`models` 루트 키가 없거나 dict 형태가 아닙니다.")
        models = {}

    # -------------------------------
    # 2) 각 모델 스키마 검사
    # -------------------------------
    for model_name, model in models.items():
        print(f"\n🎯 모델 검사: {model_name}")

        # 필수 필드 검사
        for field in REQUIRED_MODEL_FIELDS:
            if field not in model:
                errors.append(f"[{model_name}] 필드 누락: `{field}`")

        # params 검사
        params = model.get("params", {})
        if not isinstance(params, dict):
            errors.append(f"[{model_name}] params가 dict 형태가 아님")
            continue

        # params 내부 필드 검사
        for p in REQUIRED_PARAMS:
            if p not in params:
                errors.append(f"[{model_name}] params 필수값 누락: `{p}`")

        # 타입 검사
        if "default_size" in params:
            ds = params["default_size"]
            if not (isinstance(ds, list) and len(ds) == 2):
                errors.append(f"[{model_name}] default_size는 길이 2 리스트여야 합니다. → 현재: {ds}")

        if "max_size" in params:
            ms = params["max_size"]
            if not (isinstance(ms, list) and len(ms) == 2):
                errors.append(f"[{model_name}] max_size는 길이 2 리스트여야 합니다. → 현재: {ms}")

        if "guidance_scale" in params:
            gs = params["guidance_scale"]
            if gs is not None and not isinstance(gs, (int, float)):
                errors.append(f"[{model_name}] guidance_scale는 숫자 또는 null이어야 합니다. → 현재: {gs}")

        # 기타 타입 체크
        if "default_steps" in params and not isinstance(params["default_steps"], int):
            errors.append(f"[{model_name}] default_steps는 int여야 합니다.")

        if "max_steps" in params and not isinstance(params["max_steps"], int):
            errors.append(f"[{model_name}] max_steps는 int여야 합니다.")

        if "supports_i2i" in params and not isinstance(params["supports_i2i"], bool):
            errors.append(f"[{model_name}] supports_i2i는 bool이어야 합니다.")

        if "use_negative_prompt" in params and not isinstance(params["use_negative_prompt"], bool):
            errors.append(f"[{model_name}] use_negative_prompt는 bool이어야 합니다.")

        print(f"    → 검사 완료")

    # -------------------------------
    # 3) runtime 설정 검사
    # -------------------------------
    runtime = config.get("runtime", {})

    if not isinstance(runtime, dict):
        errors.append("runtime 설정이 dict가 아닙니다.")
    else:
        if "primary_model" in runtime:
            if runtime["primary_model"] not in models:
                errors.append(
                    f"runtime.primary_model = '{runtime['primary_model']}' 는 models에 존재하지 않습니다."
                )

        if "fallback_models" in runtime:
            for fm in runtime["fallback_models"]:
                if fm not in models:
                    errors.append(
                        f"runtime.fallback_models 항목 '{fm}' 이 models에 존재하지 않습니다."
                    )

    # -------------------------------
    # 결과 출력
    # -------------------------------
    print("\n=======================")
    print("🔎 검사 결과")
    print("=======================\n")

    if errors:
        print(f"❌ 총 {len(errors)}개의 문제가 발견되었습니다:\n")
        for err in errors:
            print(" - " + err)
        print("\n⚠ 위 문제를 반드시 수정해야 백엔드가 정상적으로 부팅됩니다.")
    else:
        print("✅ model_config.yaml은 완전히 유효합니다! 🎉")


if __name__ == "__main__":
    validate_model_config()
