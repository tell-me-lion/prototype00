import os
import re
import json
import argparse
import time
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

import google.genai as genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

class FactExtractor:
    def __init__(self, use_gemini=True, use_ollama=False, ollama_url="http://localhost:11434/api/generate", ollama_model="llama-3"):
        self.use_gemini = use_gemini
        self.use_ollama = use_ollama
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        
        # 기본 패턴 엔진 (규칙 기반 탐지 - 빠른 속도, 떨어지는 유연성)
        self.patterns = [
            (re.compile(r"([^ ]+(?:란|이란|은|는)).*?([^ ]+(?:이다|입니다|된다|됩니다|의미합니다))\b"), "definition"),
            (re.compile(r"([^ ]+)\s+(?:방법|순서|과정)[은|는].*?(?:이다|입니다|된다|됩니다)\b"), "procedure"),
        ]
        
        # Gemini 설정
        if self.use_gemini:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                self.model_name = "gemini-2.5-flash"
                self.gen_config = types.GenerateContentConfig(
                    system_instruction=(
                        "당신은 IT 프로그래밍 강의 스크립트에서 기술적 사실(Fact) 및 지식 명제를 추출하는 데이터 엔지니어입니다.\n"
                        "아래 규칙에 따라 지식 명제들을 JSON 배열로만 반환하세요.\n"
                        "1. 강사의 사담, 인사말, 의미 없는 문장은 철저히 배제하세요.\n"
                        "2. \"[개념]란 [설명]이다.\" 와 같은 명확한 정의나 IT 지식, 규칙, 핵심 절차만 추출하세요.\n"
                        "3. 반드시 다음과 같은 JSON 포맷의 리스트로 응답하세요. 백틱(`) 없이 순수 JSON 문자열만 출력하세요.\n"
                        "예시: [{\"type\": \"definition\", \"concept\": \"트랜잭션\", \"fact\": \"트랜잭션이란 데이터베이스의 상태를 변화시키는 작업의 단위이다.\"}]"
                    ),
                    temperature=0.1,
                    top_p=0.9,
                    response_mime_type="application/json"  # 강제 JSON 모드 출력
                )
            else:
                self.client = None
                print("[Warning] GOOGLE_API_KEY is not set. Gemini API disabled.")

    def extract_pattern(self, text: str) -> list[dict]:
        """정규식을 활용한 1차 패턴 기반 명제 추출"""
        propositions = []
        for sent in text.split(". "):
            sent = sent.strip()
            for pattern, p_type in self.patterns:
                match = pattern.search(sent)
                if match:
                    concept_guess = match.group(1).replace("이란", "").replace("란", "").replace("은", "").replace("는", "").strip()
                    propositions.append({
                        "type": p_type,
                        "concept": concept_guess,
                        "fact": sent + ("." if not sent.endswith(".") else ""),
                        "method": "pattern"
                    })
        return propositions
        
    def extract_llm(self, text: str, keywords: list) -> list[dict]:
        """LLM (Gemini 혹은 Ollama)을 활용한 심층 명제 추출"""
        if not text.strip(): 
            return []
        
        prompt = f"다음 코퍼스 텍스트 덩어리에서 중요한 지식 명제를 모두 뽑아주세요.\n[참고 핵심 키워드]: {', '.join(keywords)}\n\n[텍스트 원문]\n{text}"
        
        # ★ Ollama가 활성화되어 있으면 최우선으로 로컬 GPU 모델 사용
        if self.use_ollama:
            import requests
            try:
                payload = {
                    "model": self.ollama_model,
                    "prompt": (
                        "당신은 IT 프로그래밍 강의 스크립트에서 기술적 사실(Fact) 및 지식 명제를 추출하는 데이터 엔지니어입니다.\n"
                        "아래 규칙에 따라 지식 명제들을 JSON 배열로만 반환하세요.\n"
                        "1. 강사의 사담, 인사말, 의미 없는 문장은 철저히 배제하세요.\n"
                        "2. \"[개념]란 [설명]이다.\" 와 같은 명확한 정의나 IT 지식, 규칙, 핵심 절차만 추출하세요.\n"
                        "3. 반드시 다음과 같은 JSON 포맷의 리스트로 응답하세요.\n"
                        '예시: [{"type": "definition", "concept": "트랜잭션", "fact": "트랜잭션이란 데이터베이스의 상태를 변화시키는 작업의 단위이다."}]\n\n'
                        + prompt
                    ),
                    "stream": False,
                    "format": "json",
                    "options": {
                        "num_ctx": 4096,
                        "num_gpu": 99
                    }
                }
                res = requests.post(self.ollama_url, json=payload, timeout=120)
                data = res.json()
                
                raw = data.get("response", "").strip()
                if not raw:
                    return []
                
                parsed = json.loads(raw)
                # 모델이 리스트가 아닌 단일 객체를 반환한 경우 감싸기
                if isinstance(parsed, dict):
                    return [parsed]
                elif isinstance(parsed, list):
                    return parsed
                else:
                    return []
                    
            except json.JSONDecodeError:
                # 모델이 유효한 JSON을 못 뱉은 경우 (빈번하게 발생 가능)
                return []
            except requests.exceptions.ConnectionError:
                print(f"[Ollama Error] 연결 실패 - Ollama 서버가 실행 중인지 확인하세요.")
                return []
            except Exception as e:
                print(f"[Ollama Error] 추출 실패: {e}")
                return []

        # Ollama가 비활성화된 경우, Gemini API 사용
        elif self.use_gemini and self.client:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self.gen_config
                )
                time.sleep(2)  # 무료 호출 Rate Limit 안정성 확보

                res_text = response.text.strip()
                if res_text.startswith("```json"):
                    res_text = res_text[7:-3]
                elif res_text.startswith("```"):
                    res_text = res_text[3:-3]

                return json.loads(res_text.strip())
            except Exception as e:
                print(f"[Gemini Error] 추출 실패: {e}")
                time.sleep(4)
                return []
                
        return []

    def process_file(self, filepath: Path, output_dir: Path) -> dict:
        day = filepath.stem
        chunks = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
                    
        stats = {"input_chunks": len(chunks), "output_props": 0}
        results = []
        prop_counter = 1
        
        # 파일별로 쪼개진 시맨틱 청크를 순회
        for chunk in tqdm(chunks, desc=f"  [지식 추출] {filepath.name}", leave=False):
            text = chunk.get("text", "")
            keywords = chunk.get("keywords", [])
            
            # 1. 속도는 빠르지만 유연성이 떨어지는 정규식 패턴을 우선 탐색합니다.
            props = self.extract_pattern(text)
            
            # 2. 내용이 30자 이상으로 넉넉하다면, 유연하고 똑똑한 LLM을 투입합니다.
            if len(text) > 30 and (self.use_gemini or self.use_ollama):
                llm_props = self.extract_llm(text, keywords)
                for lp in llm_props:
                    lp["method"] = "llm"
                props.extend(llm_props)
                
            # 포맷팅 및 병합
            for prop in props:
                # 추출된 concept과 Phase 3에서 받은 keywords를 합쳐서 후보군으로 제작
                c_candidates = list(set([prop.get("concept", "")] + keywords))
                while "" in c_candidates: c_candidates.remove("")
                
                results.append({
                    "prop_id": f"{day}_P{prop_counter:04d}",
                    "chunk_id": chunk.get("chunk_id", ""),
                    "type": prop.get("type", "fact"),
                    "text": prop.get("fact", ""),
                    "concept_candidates": c_candidates,
                    "meta": {
                        "source_sents": chunk.get("sent_ids", []),
                        "model": "gemini-2.5-flash" if self.use_gemini else ("ollama" if self.use_ollama else "pattern")
                    }
                })
                prop_counter += 1
                
        stats["output_props"] = len(results)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return stats

def main():
    parser = argparse.ArgumentParser(description="Step 04: Fact Proposition Extractor (Pattern + LLM JSON Mode)")
    parser.add_argument("--input_type", type=str, choices=["base_cleaned", "gemini_cleaned"], default="base_cleaned")
    parser.add_argument("--no_gemini", action="store_true", help="Disable Gemini API (use only patterns or Ollama)")
    parser.add_argument("--use_ollama", action="store_true", help="Enable Ollama Local SLM endpoint")
    parser.add_argument("--ollama_model", type=str, default="gpt-oss:20b", help="Target Ollama model name")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent.parent
    
    input_dir = base_dir / "data" / "phase3_chunks" / args.input_type
    output_dir = base_dir / "data" / "phase4_propositions" / args.input_type
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        print("Please run Phase 3 first.")
        return

    # 제미나이를 쓸지, 옵션을 줄지 파라미터로 설정 (기본은 Gemini 활성화)
    extractor = FactExtractor(use_gemini=not args.no_gemini, use_ollama=args.use_ollama, ollama_model=args.ollama_model)
    
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print("[ERROR] No jsonl files found!")
        return

    total_stats = {"files": 0, "input_chunks": 0, "output_props": 0}

    for filepath in jsonl_files:
        print(f"Processing {filepath.name}...")
        stats = extractor.process_file(filepath, output_dir)
        total_stats["files"] += 1
        total_stats["input_chunks"] += stats["input_chunks"]
        total_stats["output_props"] += stats["output_props"]
        print(f"  [OK] {filepath.name} (chunk {stats['input_chunks']} -> prop {stats['output_props']})")

    print(f"\n{'='*60}")
    print(f"[Phase 4 전체 통계 ({args.input_type})]")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 청크 수:   {total_stats['input_chunks']}")
    print(f"  지식 명제 수:   {total_stats['output_props']}")

if __name__ == "__main__":
    main()
