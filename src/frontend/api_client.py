# Api 호출 모듈

import requests
import os

# Docker 환경이나 로컬 환경에 따라 URL이 달라질 수 있으므로 환경변수 처리 추천
# 기본값은 로컬 테스트용 localhost:8000
API_URL = os.getenv("API_URL", "http://localhost:8000")

def request_ad_generation(image_file, target, purpose):
    try:
        files = {"file": (image_file.name, image_file, image_file.type)}
        data = {"target": target, "purpose": purpose}
        
        response = requests.post(f"{API_URL}/generate", files=files, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
            
    except requests.exceptions.ConnectionError:
        return {"error": "백엔드 서버와 연결할 수 없습니다. (Backend가 켜져 있나요?)"}