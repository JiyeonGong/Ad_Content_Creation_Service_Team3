# 엑셀 파일을 json으로 변환하는 코드

import pandas as pd
import os
import json

# 1. 엑셀 파일 경로 
RESULT_DIR = "Ad_Content_Creation_Service_Team3/result"
excel_file = os.path.join(RESULT_DIR, "AI_Ad_Evaluation_Report.xlsx")
json_file = os.path.join(RESULT_DIR, "AI_Ad_Evaluation_Report.json")

# 2. 엑셀 불러오기 및 JSON 변환
if os.path.exists(excel_file):
    print(f"📂 엑셀 파일 읽는 중: {excel_file}")
    df = pd.read_excel(excel_file)
    
    # JSON 문자열로 변환 (한글 깨짐 방지 force_ascii=False)
    json_result = df.to_json(orient="records", force_ascii=False, indent=4)
    
    # 3. 파일로 저장
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(json_result)
    
    print(f"✨ JSON 변환 완료! 파일 저장됨: {json_file}")
    print("-" * 50)
    
    # 4. 화면에 출력 
    print(json_result)
    print("-" * 50)

else:
    print(f"❌ 파일을 찾을 수 없습니다: {excel_file}")