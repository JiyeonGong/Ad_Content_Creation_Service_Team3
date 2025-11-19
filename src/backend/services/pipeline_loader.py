# import os, torch
# from diffusers import DiffusionPipeline, StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, AutoPipelineForImage2Image
# from core.config import PRIMARY_MODEL, FALLBACK_MODEL, USE_FALLBACK, HF_API_TOKEN

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# T2I_PIPE = None
# I2I_PIPE = None
# CURRENT_MODEL = None
# CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache", "hf_models")
# os.makedirs(CACHE_DIR, exist_ok=True)

# def init_image_pipelines():
#     global T2I_PIPE, I2I_PIPE, CURRENT_MODEL, DEVICE
#     if T2I_PIPE:
#         print(f"ℹ️ 모델 이미 로드됨: {CURRENT_MODEL}")
#         return

#     dtype = torch.float16 if DEVICE=="cuda" else torch.float32
#     use_auth_token = HF_API_TOKEN if HF_API_TOKEN else None

#     # 1차: PRIMARY_MODEL
#     try:
#         print(f"🔄 {PRIMARY_MODEL} 로딩...")
#         T2I_PIPE = DiffusionPipeline.from_pretrained(PRIMARY_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
#         try:
#             I2I_PIPE = AutoPipelineForImage2Image.from_pipe(T2I_PIPE)
#         except:
#             I2I_PIPE = T2I_PIPE
#         CURRENT_MODEL = PRIMARY_MODEL
#         print(f"✅ {PRIMARY_MODEL} 로딩 성공")
#         return
#     except Exception as e:
#         print(f"⚠️ PRIMARY_MODEL 실패: {e}")
#         if not USE_FALLBACK:
#             T2I_PIPE = I2I_PIPE = None
#             return

#     # 2차: FALLBACK_MODEL
#     try:
#         print(f"🔄 FALLBACK_MODEL ({FALLBACK_MODEL}) 로딩...")
#         T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(FALLBACK_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
#         I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(FALLBACK_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
#         CURRENT_MODEL = FALLBACK_MODEL
#         print(f"✅ FALLBACK_MODEL 로딩 성공")
#     except Exception as e:
#         print(f"❌ 모델 로딩 실패: {e}")
#         T2I_PIPE = I2I_PIPE = CURRENT_MODEL = None



#     if T2I_PIPE:
#         print(f"✅ T2I_PIPE 정상 초기화 완료: {CURRENT_MODEL}, device: {DEVICE}")
#     else:
#         print("❌ T2I_PIPE 초기화 실패")
    
    








import os, torch
from diffusers import DiffusionPipeline, StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
from core.config import PRIMARY_MODEL, FALLBACK_MODEL, USE_FALLBACK, HF_API_TOKEN

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
T2I_PIPE = None
I2I_PIPE = None
CURRENT_MODEL = None

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache", "hf_models")
os.makedirs(CACHE_DIR, exist_ok=True)

def init_image_pipelines():
    global T2I_PIPE, I2I_PIPE, CURRENT_MODEL
    if T2I_PIPE:
        print(f"ℹ️ 모델 이미 로드됨: {CURRENT_MODEL}")
        return

    dtype = torch.float16 if DEVICE=="cuda" else torch.float32
    use_auth_token = HF_API_TOKEN if HF_API_TOKEN else None

    # 1차: PRIMARY_MODEL
    try:
        print(f"🔄 {PRIMARY_MODEL} 로딩...")
        T2I_PIPE = DiffusionPipeline.from_pretrained(PRIMARY_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
        try:
            I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(PRIMARY_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
        except:
            I2I_PIPE = T2I_PIPE
        CURRENT_MODEL = PRIMARY_MODEL
        print(f"✅ {PRIMARY_MODEL} 로딩 성공")
        return
    except Exception as e:
        print(f"⚠️ PRIMARY_MODEL 실패: {e}")
        if not USE_FALLBACK:
            T2I_PIPE = I2I_PIPE = None
            return

    # 2차: FALLBACK_MODEL
    try:
        print(f"🔄 FALLBACK_MODEL ({FALLBACK_MODEL}) 로딩...")
        T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(FALLBACK_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
        I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(FALLBACK_MODEL, cache_dir=CACHE_DIR, torch_dtype=dtype, use_auth_token=use_auth_token).to(DEVICE)
        CURRENT_MODEL = FALLBACK_MODEL
        print(f"✅ T2I_PIPE 정상 초기화 완료: {CURRENT_MODEL}, device: {DEVICE}")
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        T2I_PIPE = I2I_PIPE = CURRENT_MODEL = None