# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\outfitanyone\localtest.py

# 제공하고 있는 코드
# from gradio_client import Client, handle_file

# client = Client("HumanAIGC/OutfitAnyone")
# result = client.predict(
# 		model_name=handle_file('https://humanaigc-outfitanyone.hf.space/file=/tmp/gradio/28dbd2deba1e160bfadffbc3675ba4dcac20ca58/Eva_0.png'),
# 		garment1=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
# 		garment2=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
# 		api_name="/get_tryon_result"
# )
# print(result)

# 수정 코드
import os
import shutil
from datetime import datetime
from gradio_client import Client, handle_file

# Hugging Face Space 클라이언트
client = Client("HumanAIGC/OutfitAnyone")

# 이미지 입력 (원하는 파일로 바꾸세요)
person_img = handle_file(r"C:\Users\devuser\Codeit\test\outfitanyonetest1106\model\Xuanxuan_0.png")
top_img = handle_file(r"C:\Users\devuser\Codeit\test\outfitanyonetest1106\top\14245031_h.jpg")
bottom_img = handle_file(r"C:\Users\devuser\Codeit\test\outfitanyonetest1106\bottoms\0_86a0c1a1-db9f-464c-b2aa-4e7ff8cc2356.jpg")

# 결과 생성
result = client.predict(
    model_name=person_img,
    garment1=top_img,
    garment2=bottom_img,
    api_name="/get_tryon_result"
)

# ✅ results 폴더 생성
output_dir = "results"
os.makedirs(output_dir, exist_ok=True)

# ✅ 결과 이미지 시간 기반 파일명으로 저장
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(output_dir, f"tryon_result_{timestamp}.webp")
shutil.copy(result, output_path)

print(f"✅ 결과 이미지 저장 완료: {output_path}")