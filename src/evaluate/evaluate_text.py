import json
import os
import sys
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# ==============================================================================
# 1. 환경 설정

# .env 로드
load_dotenv()

# API 키 확인
if not os.getenv("OPENAI_API_KEY"):
    print("❌ [오류] OPENAI_API_KEY가 없습니다.")
    sys.exit(1)

judge_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# [설정] 결과 저장 경로
RESULT_DIR = "Ad_Content_Creation_Service_Team3/result"
os.makedirs(RESULT_DIR, exist_ok=True) 

# services.py 경로 추가
sys.path.append('Ad_Content_Creation_Service_Team3/src')

try:
    from backend.services import generate_caption_core
    print("✅ 'services.py' 로드 성공!")
except ImportError as e:
    print(f"❌ [오류] services.py 로드 실패: {e}")
    sys.exit(1)

# ==============================================================================
# 2. 테스트 시나리오 자동 생성기 

def generate_test_scenarios(tone, count=10):
    """
    특정 톤앤매너에 어울리는 테스트 케이스를 생성. 
    """
    print(f"   ↳ 🤖 AI가 '{tone}' 톤 테스트 케이스 {count}개를 출제 중입니다...", end=" ", flush=True)
    
    system_prompt = """
    You are a data generator. Output only valid JSON.
    Create a list of marketing request scenarios.
    """
    
    # 프롬프트에 'scenarios' 키를 가진 JSON 구조를 명확히 예시로 준다.
    user_prompt = f"""
    Generate {count} marketing request scenarios for the tone: "{tone}".
    
    You must respond with a JSON object containing a key "scenarios".
    The value of "scenarios" must be a list of objects.

    Example format:
    {{
      "scenarios": [
        {{
          "service_type": "Gym",
          "location": "Gangnam",
          "product_name": "30-day Challenge",
          "features": "1:1 PT, Diet app"
        }}
      ]
    }}
    
    Required keys in each object: "service_type", "location", "product_name", "features".
    Ensure all values are in Korean.
    """
    
    try:
        response = judge_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}, # JSON 모드 강제
            temperature=0.8 
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # 데이터 구조 유연하게 처리
        if "scenarios" in data:
            return data["scenarios"]
        else:
            # 혹시 scenarios 키 없이 바로 리스트가 올 경우를 대비
            # 만약 dict 형태라면 values() 중 리스트인 것을 찾음
            for val in data.values():
                if isinstance(val, list):
                    return val
            return []
            
    except Exception as e:
        print(f"⚠️ 시나리오 생성 실패: {e}")
        return []

# ==============================================================================
# 3. 평가 로직 (Judge)

def evaluate_result(inputs, generated_output, tone):
    system_prompt = "당신은 마케팅 콘텐츠 품질을 평가하는 수석 에디터입니다."
    user_prompt = f"""
    [입력 정보]
    - 서비스: {inputs.get('service_type', 'N/A')}
    - 지역: {inputs.get('location', 'N/A')}
    - 상품명: {inputs.get('product_name', 'N/A')}
    - 특징: {inputs.get('features', 'N/A')}
    - 목표 톤: {tone}

    [AI 생성 결과]
    {generated_output}

    위 내용을 바탕으로 3가지 항목을 5점 만점으로 평가하고 JSON으로 반환하세요.
    {{
        "accuracy": <점수>,
        "tone_score": <점수>,
        "attractiveness": <점수>,
        "reasoning": "<한줄 평>"
    }}
    """
    try:
        response = judge_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accuracy": 0, "tone_score": 0, "attractiveness": 0, "reasoning": "Err"}

# ==============================================================================
# 4. 메인 실행 
def main():
    TONES = [
        "친근하고 동기부여",
        "전문적이고 신뢰감",
        "재미있고 트렌디",
        "차분하고 감성적"
    ]
    
    results = []
    print(f"\n🚀 대규모 자동 평가 시작 (톤별 10개씩 총 {len(TONES)*10}개 케이스)\n")

    for tone in TONES:
        print(f"=== [{tone}] 테스트 진행 중 ===")
        
        scenarios = generate_test_scenarios(tone, count=10)
        print(f"✅ 문제 출제 완료! (총 {len(scenarios)}개)")
        
        if not scenarios:
            print("⚠️ 생성된 시나리오가 없어 넘어갑니다.")
            continue

        for i, inputs in enumerate(scenarios):
            # 데이터가 딕셔너리가 아니면 건너뛰는 안전장치
            if not isinstance(inputs, dict):
                print(f"    ⚠️ [{i+1}] 데이터 형식 오류로 건너뜀 (데이터: {str(inputs)[:20]}...)")
                continue

            product_name = inputs.get('product_name', '상품명 없음')
            print(f"    [{i+1}/{len(scenarios)}] '{product_name}' 평가 중...", end=" ", flush=True)
            
            # A. 서비스 실행
            info_dict = {
                "service_type": inputs.get('service_type', ''),
                "service_name": product_name,
                "features": inputs.get('features', ''),
                "location": inputs.get('location', '')
            }
            
            try:
                gen_text = generate_caption_core(info_dict, tone)
                
                # B. 평가 실행
                score = evaluate_result(inputs, gen_text, tone)
                print("✅")
                
                results.append({
                    "Tone": tone,
                    "Service": inputs.get('service_type'),
                    "Product": product_name,
                    "Generated_Copy": gen_text,
                    "Accuracy": score.get('accuracy'),
                    "Tone_Match": score.get('tone_score'),
                    "Attractiveness": score.get('attractiveness'),
                    "Reasoning": score.get('reasoning')
                })
            except Exception as e:
                print(f"❌ 실패 ({e})")

    # 3. 결과 저장
    if results:
        df = pd.DataFrame(results)
        save_path = os.path.join(RESULT_DIR, "AI_Ad_Evaluation_Report.xlsx")
        df.to_excel(save_path, index=False)
        
        print(f"\n✨ 모든 평가 완료!")
        print(f"📂 저장 완료: {save_path}")
        
        # 전체 평균 점수 출력
        print("\n📊 [종합 성적표]")
        try:
            print(df.groupby("Tone")[["Accuracy", "Tone_Match", "Attractiveness"]].mean())
        except:
            pass
    else:
        print("\n⚠️ 결과가 없습니다.")

if __name__ == "__main__":
    main()