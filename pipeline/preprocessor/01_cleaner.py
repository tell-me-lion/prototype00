"""
Step 01: 시간차 기반 물리적 단락 분할 및 Gemini STT 교정
- 타임스탬프를 메타데이터로 보존, 화자 ID 제거
- 인접 라인 병합 (15초 이내), 세션 자동 감지 (30분 gap)
- 사전에 기반한 고정된 필터링 대신 Gemini API를 활용한 STT 용어 및 문맥 클렌징 (선택적)
- 출력: data/phase1_sessions/{날짜}.jsonl
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import timedelta
from collections import defaultdict
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from tqdm import tqdm

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

class Cleaner:
    def __init__(self, use_gemini=False):
        # 정규식 컴파일 (타임스탬프 파싱, 화자 ID 분리)
        self.pattern_line = re.compile(r"^<(\d{2}):(\d{2}):(\d{2})>\s+[a-f0-9]+:\s*(.*)$")
        
        # 제미나이 설정
        self.use_gemini = use_gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        if self.use_gemini and api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"
            self.gen_config = types.GenerateContentConfig(
                system_instruction=(
                    "당신은 한국어 STT(문자 변환) 결과를 전문적으로 교정하는 보조입니다. "
                    "강의 내용 중 잘못 변환된 IT 전문 용어 등을 문맥에 맞게 수정하여 반환하세요. "
                    "요약하거나 문장 구조를 바꾸지 말고 오직 오탈자와 불필요한 단어나 추임새(어..., 그... 등) 제거에만 집중하여 정제된 텍스트 원문만 반환하세요."
                ),
                temperature=0.1,
                top_p=0.9
            )
        else:
            self.client = None
            if self.use_gemini:
                print("[Warning] GOOGLE_API_KEY is not set. Gemini API will be disabled.")

    def parse_time(self, h: str, m: str, s: str) -> timedelta:
        return timedelta(hours=int(h), minutes=int(m), seconds=int(s))

    def format_time(self, td: timedelta) -> str:
        total = int(td.total_seconds())
        hh = total // 3600
        mm = (total % 3600) // 60
        ss = total % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    def parse_lines(self, filepath: Path) -> list[dict]:
        """원본 파일에서 (time, text) 라인 목록 추출"""
        lines = []
        with open(filepath, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                match = self.pattern_line.match(raw)
                if match:
                    h, m, s, text = match.groups()
                    text = text.strip()
                    if text:
                        lines.append({
                            "time": self.parse_time(h, m, s),
                            "text": text,
                        })
        return lines

    def clean_text_gemini(self, text: str) -> str:
        """Gemini API를 이용한 문맥 기반 교정 및 추임새 제거"""
        if not self.client or len(text.strip()) < 10:
            return text
            
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"다음 텍스트의 STT 오류(특히 IT 용어)를 수정하고 불필요한 추임새를 제거해주세요. 원래의 맥락을 해치지 않는 선에서 문맥을 자연스럽게 교정하여 텍스트만 곧바로 반환하세요:\n\n{text}",
                config=self.gen_config
            )
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini Error]: {e}")
            return text

    def detect_sessions(self, paragraphs: list[dict], session_gap_min: int = 30) -> list[dict]:
        """세션 자동 감지 (시간 gap >= session_gap_min분이면 새 세션)"""
        if not paragraphs:
            return []

        session = 1
        result = []

        for i, para in enumerate(paragraphs):
            if i > 0:
                gap_min = (para["time"] - paragraphs[i - 1]["time"]).total_seconds() / 60
                if gap_min >= session_gap_min:
                    session += 1
            result.append({**para, "session": session})

        return result

    def extract_date(self, filename: str) -> str:
        """파일명에서 날짜 추출: 2026-02-02_kdt-... -> 2026-02-02"""
        match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
        return match.group(1) if match else filename.replace(".txt", "")

    def process_file(self, filepath: Path, output_dir: Path):
        """단일 파일 처리 -> 클리닝된 단락 리스트 jsonl 저장"""
        day = self.extract_date(filepath.name)

        # 1) 라인 파싱
        lines = self.parse_lines(filepath)
        stats = {"raw_lines": len(lines)}

        # 2) 세션 자동 감지 (병합 없음)
        paragraphs = self.detect_sessions(lines)
        stats["paragraphs"] = len(paragraphs)

        # 3) 출력 포맷팅 및 선택적 Gemini 클리닝
        result = []
        
        # 진행상황을 보여주기 위해 tqdm으로 감쌉니다.
        for para in tqdm(paragraphs, desc=f"  >> {filepath.name} 정제 중", leave=False):
            text = para["text"].strip()
            # 다중 공백 압축
            text = re.sub(r"\s{2,}", " ", text)
            
            if not text:
                continue
                
            # Gemini가 활성화되었다면 여기서 병합된 하나의 단락(Paragraph) 모델을 호출
            if self.use_gemini:
                text = self.clean_text_gemini(text)
                
            result.append({
                "chunk_id": filepath.stem,
                "source_file": filepath.name,
                "session": para["session"],
                "time": self.format_time(para["time"]),
                "paragraph": text,
            })

        stats["output_paragraphs"] = len(result)
        
        # 파일 저장
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in result:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return result, stats

def main():
    parser = argparse.ArgumentParser(description="Step 01: Preprocessor Cleaner (Gap Merge & Gemini STT Correction)")
    parser.add_argument("--input", type=str, default="data/raw", help="Input directory")
    parser.add_argument("--output", type=str, default="data/phase1_sessions", help="Output directory")
    parser.add_argument("--gemini", action="store_true", help="Use Gemini API for text correction")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent.parent
    input_dir = base_dir / args.input
    output_dir = base_dir / args.output
    
    # 제미나이 사용 여부에 따라 결과물 폴더 분리
    if args.gemini:
        output_dir = output_dir / "gemini_cleaned"
    else:
        output_dir = output_dir / "base_cleaned"
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        return

    cleaner = Cleaner(use_gemini=args.gemini)
    
    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"[ERROR] No .txt files found in '{input_dir}'")
        return

    total_stats = defaultdict(int)

    for filepath in txt_files:
        print(f"Processing {filepath.name}...")
        result, stats = cleaner.process_file(filepath, output_dir)
        
        # 통계 집계
        total_stats["files"] += 1
        for k in ["raw_lines", "paragraphs", "output_paragraphs"]:
            total_stats[k] += stats[k]

        sessions = set(r["session"] for r in result)
        day = cleaner.extract_date(filepath.name)
        print(f"  [OK] {filepath.name} -> {day}.jsonl "
              f"(line {stats['raw_lines']} -> para {stats['output_paragraphs']}, "
              f"session {len(sessions)})")

    print(f"\n{'='*60}")
    print(f"[전체 통계]")
    print(f"  파일 수:        {total_stats['files']}")
    print(f"  원본 라인:      {total_stats['raw_lines']}")
    print(f"  병합 단락:      {total_stats['paragraphs']}")
    print(f"  최종 출력:      {total_stats['output_paragraphs']}")

if __name__ == "__main__":
    main()
