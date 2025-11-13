# # C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\outfitanyone\outfitanyone_app.py
# # .venv = C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\.venv\Scripts\Activate.ps1

# 하드 코딩
# import streamlit as st
# from gradio_client import Client, handle_file
# import os
# import shutil
# from datetime import datetime


# # 기본 설정
# st.set_page_config(page_title="👗 OutfitAnyone Virtual Try-On", layout="centered")

# st.title("👗 OutfitAnyone Virtual Try-On")
# st.write("AI 모델로 가상 피팅을 체험해보세요!")

# # Hugging Face Space 클라이언트 생성
# client = Client("HumanAIGC/OutfitAnyone")

# # --- 업로드 영역 ---
# st.subheader("1️⃣ 이미지 업로드")
# st.caption("PNG 형식을 지원합니다.")

# model_img = st.file_uploader(
#     "모델(사람) 이미지를 업로드하세요",
#     type=["png"]
# )
# garment1_img = st.file_uploader(
#     "상의 이미지를 업로드하세요",
#     type=["png"]
# )
# garment2_img = st.file_uploader(
#     "하의 이미지를 업로드하세요 (선택)",
#     type=["png"]
# )

# # --- 실행 버튼 ---
# if st.button("✨ 가상 착용 이미지 생성"):
#     if model_img is None or garment1_img is None:
#         st.warning("👆 모델 이미지와 상의 이미지를 모두 업로드해주세요.")
#     else:
#         with st.spinner("AI가 가상 피팅 이미지를 생성 중입니다... ⏳"):
#             # 업로드된 이미지를 임시 파일로 저장
#             tmp_dir = r"C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\experiments\tmp_image"
#             os.makedirs(tmp_dir, exist_ok=True)
#             model_path = os.path.join(tmp_dir, model_img.name)
#             garment1_path = os.path.join(tmp_dir, garment1_img.name)
#             garment2_path = os.path.join(tmp_dir, garment2_img.name) if garment2_img else None

#             with open(model_path, "wb") as f:
#                 f.write(model_img.read())
#             with open(garment1_path, "wb") as f:
#                 f.write(garment1_img.read())
#             if garment2_img:
#                 with open(garment2_path, "wb") as f:
#                     f.write(garment2_img.read())

#             # Hugging Face API 호출
#             result = client.predict(
#                 model_name=handle_file(model_path),
#                 garment1=handle_file(garment1_path),
#                 garment2=handle_file(garment2_path) if garment2_img else None,
#                 api_name="/get_tryon_result"
#             )

#             # 결과 폴더 생성
#             result_dir = r"C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\experiments\outputanyone_results"
#             os.makedirs(result_dir, exist_ok=True)

#             # 결과 저장
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             output_path = os.path.join(result_dir, f"tryon_result_{timestamp}.webp")

#             shutil.copy(result, output_path)

#             # 결과 출력
#             st.success("✅ 가상 착용 이미지 생성 완료!")
#             st.image(output_path, caption="AI 착용 결과", width='stretch')
#             # For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.

#             # 다운로드 버튼
#             with open(output_path, "rb") as f:
#                 st.download_button(
#                     label="💾 결과 이미지 다운로드",
#                     data=f,
#                     file_name=f"tryon_result_{timestamp}.webp",
#                     mime="image/webp"
#                 )

#             # ---------- 임시 파일 정리 ----------
#             shutil.rmtree(tmp_dir, ignore_errors=True)







# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\outfitanyone\outfitanyone_app.py

# 모듈화

import streamlit as st

from gradio_client import Client, handle_file

import shutil

from datetime import datetime

from pathlib import Path



# src/outfitanyone 패키지 내부 import

import config

import utils



# 기본 설정

st.set_page_config(page_title="👗 OutfitAnyone Virtual Try-On", layout="centered")

st.title("👗 OutfitAnyone Virtual Try-On")

st.write("AI 모델로 가상 피팅을 체험해보세요!")



client = Client(config.HF_MODEL)



# --- 업로드 영역 ---

st.subheader("1️⃣ 이미지 업로드")

st.caption("PNG 형식을 지원합니다.")



model_img = st.file_uploader("모델 이미지 업로드", type=["png"])

garment1_img = st.file_uploader("상의 이미지 업로드", type=["png"])

garment2_img = st.file_uploader("하의 이미지 업로드 (선택)", type=["png"])



# --- 실행 버튼 ---

if st.button("✨ 가상 착용 이미지 생성"):

    if model_img is None or garment1_img is None:

        st.warning("👆 모델 이미지와 상의를 모두 업로드해주세요.")

    else:

        with st.spinner("AI가 가상 피팅 이미지를 생성 중입니다... ⏳"):

            # 임시 파일 저장

            tmp_dir = config.TMP_DIR

            utils.clear_tmp_folder(tmp_dir)

            model_path = utils.save_uploaded_file(model_img, tmp_dir)

            garment1_path = utils.save_uploaded_file(garment1_img, tmp_dir)

            garment2_path = utils.save_uploaded_file(garment2_img, tmp_dir) if garment2_img else None



            # Hugging Face API 호출

            result = client.predict(

                model_name=handle_file(model_path),

                garment1=handle_file(garment1_path),

                garment2=handle_file(garment2_path) if garment2_img else None,

                api_name=config.HF_API_NAME

            )



            # 결과 저장

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_path = config.RESULT_DIR / f"tryon_result_{timestamp}.webp"

            shutil.copy(result, output_path)



            # 결과 출력

            st.success("✅ 가상 착용 이미지 생성 완료!")

            st.image(output_path, caption="AI 착용 결과", use_column_width=True)



            # 다운로드 버튼

            with open(output_path, "rb") as f:

                st.download_button(

                    label="💾 결과 이미지 다운로드",

                    data=f,

                    file_name=output_path.name,

                    mime="image/webp"

                )




