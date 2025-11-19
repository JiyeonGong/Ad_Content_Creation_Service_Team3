import yaml, os

YAML_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "model_params.yaml")
with open(YAML_PATH, "r", encoding="utf-8") as f:
    MODEL_PARAMS = yaml.safe_load(f)

def get_model_params(model_name: str) -> dict:
    if not model_name:
        return {}
    if "FLUX" in model_name.upper():
        return MODEL_PARAMS.get("FLUX", {})
    else:
        return MODEL_PARAMS.get("SDXL", {})