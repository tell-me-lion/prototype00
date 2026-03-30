"""
Phase 1: 데이터 분리 및 물리적 세척 (Cleaner)
시간 흐름에 따른 맥락 보존을 위해 발화 구간을 병합하거나 세션을 분할하며,
문맥 기반으로 오탈자 교정 및 추임새를 제거합니다.
"""
import os
import re
import json
import argparse
import time
from pathlib import Path
from datetime import timedelta
from collections import defaultdict
from typing import Any

import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from tqdm import tqdm

from pipeline import paths

load_dotenv(paths.ROOT / '.env')

class Cleaner:
    def __init__(self, use_gemini: bool = False) -> None:
        self.pattern_line = re.compile(r"^<(\d{2}):(\d{2}):(\d{2})>\s+[a-f0-9]+:\s*(.*)$")
        self.pattern_gemini_out = re.compile(r"^<?(\d{2}:\d{2}:\d{2})>?\s*(.*)$")
        
        self.use_gemini = use_gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        if self.use_gemini and api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"
            self.gen_config = types.GenerateContentConfig(
                system_instruction=(
                    "당신은 한국어 STT(문자 변환) 결과를 전문적으로 교정하는 보조입니다. "
                    "아래 텍스트는 <HH:MM:SS> 텍스트 형태의 여러 라인으로 묶여서 입력됩니다.\n"
                    "1. 각 라인 맨 앞의 시간 태그 <HH:MM:SS>는 절대로 삭제하거나 양식을 수정하지 말고 그대로 출력하세요.\n"
                    "2. IT 전문 용어 오탈자를 문맥에 맞게 수정하고, 불필요한 단어나 추임새(어..., 그... 등)를 제거하세요.\n"
                    "3. 절대로 요약하거나 라인을 제멋대로 하나로 통합하지 마세요. (입력된 각 라인을 1:1로 대응하여 교정된 라인들로 반환)"
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

    def parse_lines(self, filepath: Path) -> list[dict[str, Any]]:
        """원본 파일에서 (time, text) 라인 목록 추출"""
        lines: list[dict[str, Any]] = []
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

    def clean_lines_gemini_batch(self, lines: list[dict[str, Any]], batch_size: int = 100) -> list[dict[str, Any]]:
        """개별 라인들을 일정 묶음(배치) 단위로 패킹/모아서 Gemini로 한 방에 정제한 뒤, 다시 분리하여 반환"""
        if not self.client or not lines:
            return lines

        cleaned_lines: list[dict[str, Any]] = []
        batches = [lines[i:i + batch_size] for i in range(0, len(lines), batch_size)]
        
        for batch in tqdm(batches, desc="  [Gemini API 배치 일괄 정제]", leave=False):
            batch_text = "\n".join([f"<{self.format_time(line['time'])}> {line['text']}" for line in batch])
            
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=f"[입력 텍스트]\n{batch_text}",
                    config=self.gen_config
                )
                res_text = response.text.strip()
                
                for out_line in res_text.splitlines():
                    out_line = out_line.strip()
                    if not out_line: continue
                    
                    match = self.pattern_gemini_out.match(out_line)
                    if match:
                        time_str, cleaned_text = match.groups()
                        h, m, s = time_str.split(":")
                        if cleaned_text.strip():
                            cleaned_lines.append({
                                "time": self.parse_time(h, m, s),
                                "text": cleaned_text.strip()
                            })
                    else:
                        pass
                
                time.sleep(1.5)
                
            except Exception as e:
                print(f"\n[Gemini Error] 일괄 정제 실패. 해당 구간은 원본 사용. Error: {e}")
                cleaned_lines.extend(batch)
                time.sleep(5)
                
        cleaned_lines.sort(key=lambda x: x["time"])
        return cleaned_lines

    def merge_lines(self, lines: list[dict[str, Any]], max_gap_sec: int = 15) -> list[dict[str, Any]]:
        """인접 라인 병합 (직전 발화와의 시간 간격 <= max_gap_sec)"""
        if not lines:
            return []

        paragraphs: list[dict[str, Any]] = []
        current_start_time = lines[0]["time"]
        last_line_time = lines[0]["time"]
        current_texts = [lines[0]["text"]]

        for line in lines[1:]:
            gap = (line["time"] - last_line_time).total_seconds()
            if 0 <= gap <= max_gap_sec:
                current_texts.append(line["text"])
            else:
                paragraphs.append({
                    "time": current_start_time,
                    "end_time": last_line_time,
                    "text": " ".join(current_texts),
                })
                current_start_time = line["time"]
                current_texts = [line["text"]]
            last_line_time = line["time"]

        paragraphs.append({
            "time": current_start_time,
            "end_time": last_line_time,
            "text": " ".join(current_texts),
        })

        return paragraphs

    def detect_sessions(self, paragraphs: list[dict[str, Any]], session_gap_min: int = 30) -> list[dict[str, Any]]:
        """세션 자동 감지 (시간 gap >= session_gap_min분이면 새 세션)"""
        if not paragraphs:
            return []

        session = 1
        result: list[dict[str, Any]] = []

        for i, para in enumerate(paragraphs):
            if i > 0:
                gap_min = (para["time"] - paragraphs[i - 1]["end_time"]).total_seconds() / 60
                if gap_min >= session_gap_min:
                    session += 1
            result.append({**para, "session": session})

        return result

    def extract_date(self, filename: str) -> str:
        """파일명에서 날짜 추출: 2026-02-02_kdt-... -> 2026-02-02"""
        match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
        return match.group(1) if match else filename.replace(".txt", "")

    def process_file(self, filepath: Path, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """단일 파일 처리 -> 클리닝된 단락 리스트 jsonl 저장"""
        day = self.extract_date(filepath.name)

        lines = self.parse_lines(filepath)
        stats = {"raw_lines": len(lines)}

        if self.use_gemini:
            lines = self.clean_lines_gemini_batch(lines, batch_size=100)

        paragraphs = self.merge_lines(lines)
        stats["paragraphs"] = len(paragraphs)

        paragraphs = self.detect_sessions(paragraphs)

        result: list[dict[str, Any]] = []
        for para in paragraphs:
            text = para["text"].strip()
            text = re.sub(r"\s{2,}", " ", text)
            
            if not text:
                continue
                
            result.append({
                "chunk_id": filepath.stem,
                "source_file": filepath.name,
                "session": para["session"],
                "time": self.format_time(para["time"]),
                "paragraph": text,
                "processing_type": "gemini" if self.use_gemini else "base"
            })

        stats["output_paragraphs"] = len(result)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in result:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return result, stats

def main() -> None:
    parser = argparse.ArgumentParser(description="Step 01: Preprocessor Cleaner (Gap Merge & Gemini STT Correction)")
    parser.add_argument("--gemini", action="store_true", help="Use Gemini API for text correction")
    args = parser.parse_args()

    input_dir = paths.DATA_RAW
    output_dir = paths.DATA_PHASE1_SESSIONS
    
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
