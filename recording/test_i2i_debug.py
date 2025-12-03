#!/usr/bin/env python3
"""
페이지 3 I2I 이미지 스타일 변경 디버깅 테스트

목표: 입력 이미지와 프롬프트가 제대로 전달되는지 확인
"""
import requests
import base64
import json
import sys
from pathlib import Path
from PIL import Image
import io

API_URL = "http://localhost:8000"

def create_test_image(text: str, size: int = 512) -> bytes:
    """테스트 이미지 생성 (텍스트 포함)"""
    img = Image.new('RGB', (size, size), color='white')
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    
    # 텍스트 그리기
    draw.text((50, size//2), text, fill='black')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def test_i2i_with_different_images():
    """다양한 입력 이미지로 I2I 테스트"""
    
    test_cases = [
        {
            "name": "테스트 1: 빨간색 배경",
            "image": create_test_image("RED", 512),
            "prompt": "초록색 배경으로 변경, 밝고 생생한 분위기"
        },
        {
            "name": "테스트 2: 파란색 배경",
            "image": create_test_image("BLUE", 512),
            "prompt": "노란색 배경으로 변경, 따뜻한 분위기"
        },
        {
            "name": "테스트 3: 검은색 배경",
            "image": create_test_image("BLACK", 512),
            "prompt": "흰색 배경으로 변경, 깔끔한 분위기"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 {test_case['name']}")
        print(f"{'='*60}")
        
        # 입력 이미지 정보 출력
        image_data = test_case['image']
        print(f"📷 입력 이미지 크기: {len(image_data)} bytes")
        print(f"📝 프롬프트: {test_case['prompt']}")
        
        # Base64 인코딩
        image_base64 = base64.b64encode(image_data).decode()
        print(f"📊 Base64 길이: {len(image_base64)} chars")
        
        # API 요청 구성
        payload = {
            "input_image_base64": image_base64,
            "prompt": test_case['prompt'],
            "strength": 0.75,
            "width": 512,
            "height": 512,
            "steps": 20,
            "guidance_scale": 5.0,
            "post_process_method": "none",
            "enable_adetailer": False,
            "adetailer_targets": None,
            "model_name": "flux_dev"  # FLUX 모델 명시
        }
        
        print(f"\n🚀 API 요청 전송...")
        print(f"   엔드포인트: POST {API_URL}/api/generate_i2i")
        print(f"   Payload 필드: {list(payload.keys())}")
        print(f"   Model: {payload.get('model_name')}")
        
        try:
            response = requests.post(
                f"{API_URL}/api/generate_i2i",
                json=payload,
                timeout=600
            )
            
            print(f"\n📋 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                output_base64 = data.get("image_base64", "")
                print(f"✅ 성공!")
                print(f"   출력 이미지 크기: {len(output_base64)} bytes")
                
                # 결과 이미지 저장
                output_bytes = base64.b64decode(output_base64)
                output_path = f"/tmp/i2i_test_{len(test_cases)}.png"
                with open(output_path, 'wb') as f:
                    f.write(output_bytes)
                print(f"   저장 경로: {output_path}")
                
                # 입력/출력 이미지 비교
                print(f"\n📊 비교:")
                print(f"   입력 크기: {len(image_data)} bytes")
                print(f"   출력 크기: {len(output_bytes)} bytes")
                print(f"   크기 차이: {abs(len(output_bytes) - len(image_data))} bytes")
                
                # Base64 문자열 비교 (같으면 이미지 데이터가 동일)
                if image_base64 == output_base64:
                    print(f"   ⚠️  WARNING: 입력과 출력 이미지가 동일합니다! 스타일 변경이 작동하지 않음")
                else:
                    print(f"   ✅ 입력과 출력이 다릅니다 (정상)")
                    
            else:
                print(f"❌ 오류: {response.status_code}")
                print(f"   응답: {response.text[:500]}")
                
        except requests.exceptions.Timeout:
            print(f"⏳ 요청 시간 초과 (600초)")
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ 테스트 완료")
    print(f"{'='*60}")

if __name__ == "__main__":
    print(f"🔍 페이지 3 I2I 디버깅 테스트 시작")
    print(f"API: {API_URL}")
    print(f"현재 시간: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_i2i_with_different_images()
