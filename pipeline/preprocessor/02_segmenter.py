import os
import json
import argparse
from pathlib import Path
from kiwipiepy import Kiwi
from tqdm import tqdm

class Segmenter:
    def __init__(self):
        # 최신 kiwipiepy(v0.22.0+)의 기본 권장 모델 사용
        self.kiwi = Kiwi()
        
        # 필터링 규칙: 아래에 해당하는 실질 형태소(명사, 동사 등)가 최소 1개는 있어야 통과
        # N*: 명사류, V*: 동사/형용사류
        self.valid_pos_prefixes = ('N', 'V')

    def process_paragraph(self, paragraph: str) -> list[dict]:
        """단락(문단) 텍스트를 문장 단위로 분할하고 형태소 분석 결과를 반환합니다."""
        if not paragraph.strip():
            return []
            
        sentences = self.kiwi.split_into_sents(paragraph)
        results = []
        
        for sent in sentences:
            tokens = self.kiwi.tokenize(sent.text)
            pos_tags = [token.tag for token in tokens]
            
            # 유의미한 형태소가 포함되어 있는지 확인 (명사나 동사)
            has_content = any(tag.startswith(self.valid_pos_prefixes) for tag in pos_tags)
            
            # 문장 길이가 너무 짧거나("네", "아") 실질 형태소가 없는 경우 제거 (필터링)
            if has_content and len(sent.text.strip()) >= 2:
                results.append({
                    "text": sent.text.strip(),
                    "pos_tags": pos_tags
                })
        return results

    def process_file(self, filepath: Path, output_dir: Path) -> dict:
        day = filepath.stem
        records = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
                
        stats = {"input_paras": len(records), "output_sents": 0}
        results = []
        sent_id_counter = 1
        
        for para in tqdm(records, desc=f"  [Kiwi 분리] {filepath.name}", leave=False):
            # 문장 분리 및 필터링 수행
            sents_data = self.process_paragraph(para["paragraph"])
            
            # 분리된 문장 병합 및 메타데이터 상속 포맷팅
            for s_data in sents_data:
                results.append({
                    "chunk_id": para.get("chunk_id", ""),
                    "source_file": para.get("source_file", ""),
                    "session": para.get("session", 1),
                    "time": para.get("time", ""),
                    "sent_id": sent_id_counter,
                    "text": s_data["text"],
                    "pos_tags": s_data["pos_tags"]
                })
                sent_id_counter += 1
                
        stats["output_sents"] = len(results)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return stats

def main():
    parser = argparse.ArgumentParser(description="Step 02: Preprocessor Segmenter (Kiwi sentence split & filter)")
    # Phase 1 결과물이 두 종류이므로, 어떤 폴더를 읽고/저장할지 결정
    parser.add_argument("--input_type", type=str, choices=["base_cleaned", "gemini_cleaned"], default="base_cleaned", 
                        help="Input source folder type from Phase 1 (default: base_cleaned)")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent.parent
    
    # 입출력 경로를 동적으로 구성 (data/phase2_sentences/base_cleaned 등)
    input_dir = base_dir / "data" / "phase1_sessions" / args.input_type
    output_dir = base_dir / "data" / "phase2_sentences" / args.input_type
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        print(f"Please run Phase 1 first or check your --input_type argument.")
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
    print(f"[Phase 2 전체 통계 ({args.input_type})]")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 단락 수:   {total_stats['input_paras']}")
    print(f"  추출 문장 수:   {total_stats['output_sents']}")

if __name__ == "__main__":
    main()
