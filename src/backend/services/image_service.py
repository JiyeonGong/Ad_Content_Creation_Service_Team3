# import io
# from PIL import Image
# from services.pipeline_loader import T2I_PIPE, I2I_PIPE, CURRENT_MODEL
# from services.openai_service import optimize_prompt
# from core.utils import get_model_params

# def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
#     try:
#         print("🚀 generate_t2i_core 실행됨")

#         if T2I_PIPE is None:
#             print("❌ T2I PIPELINE 미초기화")
#             raise RuntimeError("T2I PIPELINE 미초기화")

#         optimized_prompt = optimize_prompt(prompt)
#         params = get_model_params(CURRENT_MODEL)

#         gen_params = {
#             "prompt": optimized_prompt,
#             "width": width,
#             "height": height,
#             "num_inference_steps": steps if steps > 1 else params["default_steps"]
#         }

#         if params["use_negative_prompt"]:
#             gen_params["negative_prompt"] = params["negative_prompt"]

#         if params["guidance_scale"]:
#             gen_params["guidance_scale"] = params["guidance_scale"]

#         print("🔧 파라미터:", gen_params)

#         # --- pipeline 실행 ---
#         result = T2I_PIPE(**gen_params)
#         print("📌 pipeline 결과:", result)

#         # --- 이미지 검사 ---
#         if not result or not hasattr(result, "images") or len(result.images) == 0:
#             print("❌ Pipeline 결과에 이미지 없음")
#             raise ValueError("이미지가 생성되지 않았습니다.")

#         buf = io.BytesIO()
#         result.images[0].save(buf, format="PNG")
#         print("✅ 이미지 변환 성공")
#         return buf.getvalue()

#     except Exception as e:
#         print("🔥 generate_t2i_core 내부 에러 발생!")
#         import traceback
#         traceback.print_exc()      # <<< 여기서 전체 Traceback 출력됨!
#         raise

# def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, width: int, height: int, steps: int) -> bytes:
#     if I2I_PIPE is None:
#         raise RuntimeError("I2I PIPELINE 미초기화")
#     optimized_prompt = optimize_prompt(prompt)
#     input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
#     params = get_model_params(CURRENT_MODEL)
#     gen_params = {
#         "prompt": optimized_prompt,
#         "image": input_image,
#         "strength": strength,
#         "num_inference_steps": steps if steps>1 else params["default_steps"]
#     }
#     if params["use_negative_prompt"]:
#         gen_params["negative_prompt"] = params["negative_prompt"]
#     if params["guidance_scale"]:
#         gen_params["guidance_scale"] = params["guidance_scale"]
#     result = I2I_PIPE(**gen_params)
#     buf = io.BytesIO()
#     result.images[0].save(buf, format="PNG")
#     return buf.getvalue()








import io, base64
from services.pipeline_loader import T2I_PIPE, I2I_PIPE, CURRENT_MODEL

def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
    try:
        print("🚀 generate_t2i_core 실행됨")
        if T2I_PIPE is None:
            raise RuntimeError("T2I PIPELINE 미초기화")

        # 기본 pipeline 파라미터 설정
        params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps if steps>1 else 50  # 기본 50 스텝
        }

        result = T2I_PIPE(**params)

        # 이미지 유효성 확인
        if not result or not hasattr(result, "images") or len(result.images)==0:
            raise ValueError("이미지 생성 실패: 결과 이미지 없음")

        buf = io.BytesIO()
        result.images[0].save(buf, format="PNG")
        print("✅ 이미지 생성 성공")
        return buf.getvalue()

    except Exception as e:
        print("🔥 generate_t2i_core 내부 에러 발생!")
        import traceback
        traceback.print_exc()
        raise