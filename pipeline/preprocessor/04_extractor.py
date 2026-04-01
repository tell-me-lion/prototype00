"""
Phase 4: 지식 명제 추출 (Fact Extractor)
청크 텍스트 속에서 교육적으로 의미 있는 '규칙, 정의, 절차' 등의 핵심 명제(Fact 후보)를 
정규식 패턴 및 LLM(Gemini / Ollama)을 활용하여 추출합니다.
"""
import os
import re
import json
import argparse
import time
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from typing import Any

import google.genai as genai
from google.genai import types

from pipeline import paths

load_dotenv(paths.ROOT / '.env')

class FactExtractor:
    def __init__(self, use_gemini: bool = True, use_ollama: bool = False, 
                 ollama_url: str = "http://localhost:11434/api/generate", 
                 ollama_model: str = "gemma3:12b") -> None:
        self.use_gemini = use_gemini
        self.use_ollama = use_ollama
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        
        self.patterns = [
            (re.compile(r"([^ ]+(?:란|이란|은|는)).*?([^ ]+(?:이다|입니다|된다|됩니다|의미합니다))\b"), "definition"),
            (re.compile(r"([^ ]+)\s+(?:방법|순서|과정)[은|는].*?(?:이다|입니다|된다|됩니다)\b"), "procedure"),
        ]
        
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
                    response_mime_type="application/json"
                )
            else:
                self.client = None
                print("[Warning] GOOGLE_API_KEY is not set. Gemini API disabled.")

    def extract_pattern(self, text: str) -> list[dict[str, Any]]:
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
        
    def extract_llm(self, text: str, keywords: list[str]) -> list[dict[str, Any]]:
        """LLM (Gemini 혹은 Ollama)을 활용한 심층 명제 추출"""
        if not text.strip(): 
            return []
        
        prompt = f"다음 코퍼스 텍스트 덩어리에서 중요한 지식 명제를 모두 뽑아주세요.\n[참고 핵심 키워드]: {', '.join(keywords)}\n\n[텍스트 원문]\n{text}"
        
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
                if isinstance(parsed, dict):
                    return [parsed]
                elif isinstance(parsed, list):
                    return [p for p in parsed if isinstance(p, dict)]
                else:
                    return []
                    
            except json.JSONDecodeError:
                return []
            except requests.exceptions.ConnectionError:
                print(f"[Ollama Error] 연결 실패 - Ollama 서버가 실행 중인지 확인하세요.")
                return []
            except Exception as e:
                print(f"[Ollama Error] 추출 실패: {e}")
                return []

        elif self.use_gemini and self.client:
            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=self.gen_config
                    )
                    time.sleep(2)

                    res_text = response.text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text[7:-3]
                    elif res_text.startswith("```"):
                        res_text = res_text[3:-3]

                    parsed = json.loads(res_text.strip())
                    return parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    return []
                except Exception as e:
                    err_str = str(e)
                    if attempt < max_retries and ("429" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str or "UNAVAILABLE" in err_str):
                        wait_sec = 10.0 * (2 ** attempt)
                        print(f"[Gemini] 추출 재시도 ({attempt+1}/{max_retries}) — {wait_sec:.0f}초 대기: {err_str[:80]}")
                        time.sleep(wait_sec)
                    else:
                        print(f"[Gemini Error] 추출 실패: {e}")
                        time.sleep(4)
                        return []
            return []
                
        return []

    def process_file(self, filepath: Path, output_dir: Path, progress_callback=None) -> dict[str, int]:
        """
        Args:
            progress_callback: Callable[[int, int, int], None] — (청크_완료수, 총_청크수, 명제_누적수)
        """
        day = filepath.stem
        chunks = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        stats = {"input_chunks": len(chunks), "output_props": 0}
        results = []
        prop_counter = 1
        total_chunks = len(chunks)

        for i, chunk in enumerate(tqdm(chunks, desc=f"  [지식 추출] {filepath.name}", leave=False)):
            text = chunk.get("text", "")
            keywords = chunk.get("keywords", [])

            props = self.extract_pattern(text)

            if len(text) > 30 and (self.use_gemini or self.use_ollama):
                llm_props = self.extract_llm(text, keywords)
                for lp in llm_props:
                    lp["method"] = "llm"
                props.extend(llm_props)

            for prop in props:
                c_candidates = list(set([prop.get("concept", "")] + keywords))
                while "" in c_candidates: c_candidates.remove("")

                results.append({
                    "prop_id": f"{day}_P{prop_counter:04d}",
                    "chunk_id": chunk.get("chunk_id", ""),
                    "type": prop.get("type", "fact"),
                    "text": prop.get("fact", ""),
                    "concept_candidates": c_candidates,
                    "processing_type": chunk.get("processing_type", "base"),
                    "meta": {
                        "source_sents": chunk.get("sent_ids", []),
                        "model": "gemini-2.5-flash" if self.use_gemini else ("ollama" if self.use_ollama else "pattern")
                    }
                })
                prop_counter += 1

            if progress_callback:
                progress_callback(i + 1, total_chunks, len(results))

        stats["output_props"] = len(results)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return stats

def main() -> None:
    parser = argparse.ArgumentParser(description="Step 04: Fact Proposition Extractor (Pattern + LLM JSON Mode)")
    parser.add_argument("--no_gemini", action="store_true", help="Disable Gemini API (use only patterns or Ollama)")
    parser.add_argument("--use_ollama", action="store_true", help="Enable Ollama Local SLM endpoint")
    parser.add_argument("--ollama_model", type=str, default="gemma3:12b", help="Target Ollama model name")
    args = parser.parse_args()

    input_dir = paths.DATA_PHASE3_CHUNKS
    output_dir = paths.DATA_PHASE4_PROPOSITIONS
    
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
    print(f"[Phase 4 전체 통계]")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 청크 수:   {total_stats['input_chunks']}")
    print(f"  지식 명제 수:   {total_stats['output_props']}")

if __name__ == "__main__":
    main()
