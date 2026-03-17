import os
import re
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

class Cleaner:
    """
    Phase 1: 데이터 분리 및 물리적 세척
    - 시간 기반 세션 분리 (오전/오후 등)
    - 강제 오타 교정 및 정규식 기반 쓰레기값 제거
    - Gemini API를 활용한 STT 용어 클렌징
    """
    def __init__(self, config_dir=None):
        if config_dir is None:
            self.config_dir = Path(__file__).resolve().parent / "config"
        else:
            self.config_dir = Path(config_dir)
            
        self.regex_patterns = self._load_json_config("regex_patterns.json")
        self.stt_corrections = self._load_json_config("stt_corrections.json").get("corrections", {})
        
        # 정규식 컴파일
        self.pattern_line = re.compile(r"^<(\d{2}:\d{2}:\d{2})>\s+[a-f0-9]+:\s*(.*)")
        
        # 제미나이 설정
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction="당신은 한국어 STT(문자 변환) 결과를 전문적으로 교정하는 보조입니다. 강의 내용 중 잘못 변환된 IT 전문 용어 등을 문맥에 맞게 수정하여 반환하세요. 원래의 의미나 맥락을 변경하지 말고 오직 클렌징에만 집중하세요.",
                generation_config={"temperature": 0.1, "top_p": 0.9}
            )
        else:
            self.model = None
            print("[Warning] GOOGLE_API_KEY is not set. Gemini API will be disabled.")

    def _load_json_config(self, filename) -> dict:
        config_path = self.config_dir / filename
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_session_type(self, time_str):
        """시간 문자열(HH:MM:SS)을 기준으로 오전/오후 세션 구분"""
        try:
            dt = datetime.strptime(time_str, "%H:%M:%S")
            if dt.hour < 13:
                return "오전"
            else:
                return "오후"
        except:
            return "알수없음"

    def clean_text_basic(self, text):
        """사전 정의된 규칙 기반 치환"""
        # 단순 치환
        for wrong, correct in self.stt_corrections.items():
            text = text.replace(wrong, correct)
        
        # 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def clean_text_gemini(self, text):
        """Gemini API를 이용한 문맥 기반 교정"""
        if not self.model or len(text.strip()) < 10:
            return text
            
        try:
            response = self.model.generate_content(
                f"다음 텍스트의 STT 오류(특히 IT 용어)를 수정해주세요. 요약하거나 구조를 바꾸지 말고 텍스트 원문만 반환하세요:\n\n{text}"
            )
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini Error]: {e}")
            return text

    def process_file(self, file_path: Path, output_dir: Path, use_gemini=False):
        """하나의 txt 파일을 읽어서 세션별로 분할 후 정제하여 jsonl 형태로 저장"""
        file_path = Path(file_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Processing {file_path.name}...")
        
        sessions = {"오전": [], "오후": []}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                match = self.pattern_line.match(line)
                if match:
                    time_str = match.group(1)
                    content = match.group(2)
                    
                    session_type = self.get_session_type(time_str)
                    
                    # 1차 정제 (Regex + Dict)
                    cleaned_content = self.clean_text_basic(content)
                    if cleaned_content:
                        sessions[session_type].append(cleaned_content)
                else:
                    # 패턴이 맞지 않는 경우 (예: 여러 줄로 이어진 텍스트)
                    # 가장 최근에 추가된 세션에 붙임 (간단한 처리)
                    pass

        # 세션별로 텍스트 뭉치기 (단락 구성)
        output_data = []
        for session_type, sentences in sessions.items():
            if not sentences:
                continue
                
            merged_text = " ".join(sentences)
            
            # 여기서 선택적으로 Gemini 교정 도입 (긴 텍스트의 경우 청크 단위 처리 권장되나 임시 통채로 적용)
            # 텍스트가 너무 길면 API 에러가 날 수 있으므로 주의
            if use_gemini:
                merged_text = self.clean_text_gemini(merged_text)
            
            chunk_id = f"{file_path.stem}_{session_type}"
            
            output_data.append({
                "chunk_id": chunk_id,
                "source_file": file_path.name,
                "session": session_type,
                "text": merged_text
            })
            
        output_file = output_dir / f"{file_path.stem}_cleaned.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for data in output_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
                
        print(f"Saved to {output_file}")


def run_phase1_pipeline(input_dir: str, output_dir: str, use_gemini=False):
    cleaner = Cleaner()
    input_path = Path(input_dir)
    
    # 디렉토리 존재 확인
    if not input_path.exists():
        print(f"Input directory not found: {input_dir}")
        return
        
    for txt_file in input_path.glob("*.txt"):
        cleaner.process_file(txt_file, output_dir, use_gemini)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1: Preprocessor Cleaner")
    parser.add_argument("--input", type=str, default="data/raw", help="Input directory")
    parser.add_argument("--output", type=str, default="data/phase1_sessions", help="Output directory")
    parser.add_argument("--gemini", action="store_true", help="Use Gemini API for text correction")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    input_dir = base_dir / args.input
    output_dir = base_dir / args.output
    
    run_phase1_pipeline(str(input_dir), str(output_dir), args.gemini)
