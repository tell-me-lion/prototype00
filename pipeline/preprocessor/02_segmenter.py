"""
Phase 2: 문장 복원 및 필터링 (Segmenter)
발화 단위의 텍스트를 마침표가 없는 구어체까지 처리 가능한 `kiwipiepy` 형태소 분석기로
완전한 문장 단위로 분할하고, 영양가 없는 문장을 품사(POS) 기반으로 필터링합니다.
"""
import os
import json
import argparse
from pathlib import Path
from typing import Any
from kiwipiepy import Kiwi
from tqdm import tqdm

from pipeline import paths

class Segmenter:
    def __init__(self) -> None:
        self.kiwi = Kiwi()
        self.valid_pos_prefixes = ('N', 'V')

    def process_paragraph(self, paragraph: str) -> list[dict[str, Any]]:
        """단락(문단) 텍스트를 문장 단위로 분할하고 형태소 분석 결과를 반환합니다."""
        if not paragraph.strip():
            return []
            
        sentences = self.kiwi.split_into_sents(paragraph)
        results: list[dict[str, Any]] = []
        
        for sent in sentences:
            tokens = self.kiwi.tokenize(sent.text)
            pos_tags = [token.tag for token in tokens]
            
            has_content = any(tag.startswith(self.valid_pos_prefixes) for tag in pos_tags)
            
            if has_content and len(sent.text.strip()) >= 2:
                results.append({
                    "text": sent.text.strip(),
                    "pos_tags": pos_tags
                })
        return results

    def process_file(self, filepath: Path, output_dir: Path) -> dict[str, int]:
        day = filepath.stem
        records: list[dict[str, Any]] = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                
        stats = {"input_paras": len(records), "output_sents": 0}
        results: list[dict[str, Any]] = []
        sent_id_counter = 1
        
        for para in tqdm(records, desc=f"  [Kiwi 분리] {filepath.name}", leave=False):
            sents_data = self.process_paragraph(para.get("paragraph", ""))
            
            for s_data in sents_data:
                results.append({
                    "chunk_id": para.get("chunk_id", ""),
                    "source_file": para.get("source_file", ""),
                    "session": para.get("session", 1),
                    "time": para.get("time", ""),
                    "sent_id": sent_id_counter,
                    "text": s_data["text"],
                    "pos_tags": s_data["pos_tags"],
                    "processing_type": para.get("processing_type", "base")
                })
                sent_id_counter += 1
                
        stats["output_sents"] = len(results)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return stats

def main() -> None:
    parser = argparse.ArgumentParser(description="Step 02: Preprocessor Segmenter (Kiwi sentence split & filter)")
    args = parser.parse_args()

    input_dir = paths.DATA_PHASE1_SESSIONS
    output_dir = paths.DATA_PHASE2_SENTENCES
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        print(f"Please run Phase 1 first.")
        return

    segmenter = Segmenter()
    
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[ERROR] No .jsonl files found in '{input_dir}'")
        return

    total_stats = {"files": 0, "input_paras": 0, "output_sents": 0}

    for filepath in jsonl_files:
        print(f"Processing {filepath.name}...")
        stats = segmenter.process_file(filepath, output_dir)
        
        total_stats["files"] += 1
        total_stats["input_paras"] += stats["input_paras"]
        total_stats["output_sents"] += stats["output_sents"]

        print(f"  [OK] {filepath.name} -> {filepath.name} "
              f"(para {stats['input_paras']} -> sent {stats['output_sents']})")

    print(f"\n{'='*60}")
    print(f"[Phase 2 전체 통계]")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 단락 수:   {total_stats['input_paras']}")
    print(f"  추출 문장 수:   {total_stats['output_sents']}")

if __name__ == "__main__":
    main()
