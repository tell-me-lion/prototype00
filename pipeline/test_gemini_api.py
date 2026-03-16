import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")

print("API 설정 중...")
genai.configure(api_key=api_key)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction="당신은 친절하고 전문적인 AI 보조입니다. 짧고 간결하게 대답해주세요.",
    generation_config={
        "temperature": 0.4,
        "top_p": 0.9
    }
)

try:
    print("제미나이 API에 테스트 요청을 보내는 중입니다...")
    response = model.generate_content("안녕하세요! API 테스트 요청입니다. 정상적으로 응답 가능한지 확인 부탁드립니다. 한국어로 답해주세요.")
    
    llm_raw_response = response.text
    print("\n[API 응답 결과]")
    print(llm_raw_response)
except Exception as e:
    print(f"\n[에러 발생] API 요청 중 문제가 발생했습니다: {e}")
