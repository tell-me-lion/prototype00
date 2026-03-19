import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

class Formatter:
    def __init__(self):
        pass
        
    def parse_metadata_from_filename(self, filename: str) -> dict:
        """파일명에서 기수(week/th), 세션(오전/오후) 등 메타데이터 추출
        예: 2026-02-02_kdt-backendj-21th.txt -> week: 21
        """
        meta = {"week": None, "session": "Unknown"}
        
        # 기수(th) 추출
        match_th = re.search(r"(\d+)th", filename)
        if match_th:
            meta["week"] = int(match_th.group(1))
            
        # 오전/오후 추출 (파일명에 명시되어 있는 경우)
        if "오전" in filename:
            meta["session"] = "오전"
        elif "오후" in filename:
            meta["session"] = "오후"
            
        return meta

    def format_documents(self, chunks_path: Path, props_path: Path, output_dir: Path):
        # 1. 청크 데이터 로드 (Phase 3 결과물)
        chunks = {}
        if chunks_path.exists():
            with open(chunks_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        c = json.loads(line)
                        chunks[c["chunk_id"]] = c
                        
        # 2. 명제 데이터 로드 및 해당 청크별 매핑 (Phase 4 결과물)
        chunk_facts = defaultdict(list)
        all_props = []
        if props_path.exists():
            with open(props_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        p = json.loads(line)
                        chunk_facts[p["chunk_id"]].append(p)
                        all_props.append(p)

        # 3. 요청하신 Chunk 문서(API 전송용/저장용) 구축
        formatted_chunks = []
        for cid, c in chunks.items():
            # 메타데이터 파싱 (주로 소스 파일명 활용)
            meta = self.parse_metadata_from_filename(c.get("meta", {}).get("source_file", c.get("chunk_id", "")))
            
            # 이 청크에 소속된 팩트 문장들
            facts_list = [p["text"] for p in chunk_facts.get(cid, [])]
            
            formatted_chunks.append({
                "chunk_id": cid,
                "week": meta["week"],
                "session": meta["session"],
                "text": c["text"],
                "facts": facts_list,
                "tfidf_keywords": c.get("keywords", [])
            })
            
        # 4. 요청하신 Concept DB 문서 구축 (주제별 그룹화)
        concepts_db = defaultdict(lambda: {
            "definition": set(),
            "related_concepts": set(),
            "source_chunk_ids": set()
        })
        
        # 추출된 지식 명제를 바탕으로 개념(Concept) 지도 구축
        for p in all_props:
            cid = p["chunk_id"]
            candidates = p.get("concept_candidates", [])
            if not candidates:
                continue
                
            # 가장 신뢰도 높은 첫번째를 메인 개념으로 선정
            main_concept = candidates[0]
            
            # 정의(definition) 누적
            concepts_db[main_concept]["definition"].add(p["text"])
            
            # 관련 개념(동반 출현한 개념 및 TF-IDF 키워드) 추가
            for cand in candidates[1:]:
                concepts_db[main_concept]["related_concepts"].add(cand)
            if cid in chunks:
                for kw in chunks[cid].get("keywords", []):
                    if kw != main_concept:
                        concepts_db[main_concept]["related_concepts"].add(kw)
                        
            # 근거가 등장한 출처 청크 ID 수집
            concepts_db[main_concept]["source_chunk_ids"].add(cid)
            
        formatted_concepts = []
        for concept_name, data in concepts_db.items():
            # 병합된 여러 정의문들을 슬래시(/)나 줄바꿈으로 병합
            defn = " / ".join(list(data["definition"]))
            # 고유 식별자 생성
            concept_id = f"concept_{concept_name.lower().replace(' ', '_')}"
            
            formatted_concepts.append({
                "concept_id": concept_id,
                "concept": concept_name,
                "definition": defn,
                # 연관성이 떨어지는 것을 방지하기 위해 상위 7개 정도만 기록
                "related_concepts": list(data["related_concepts"])[:7], 
                "source_chunk_ids": list(data["source_chunk_ids"])
            })

        # --- 파일 저장 단계 ---
        output_dir.mkdir(parents=True, exist_ok=True)
        day = chunks_path.stem
        
        # 4-1. Chunk 기반 결과물 저장
        chunks_out = output_dir / f"{day}_chunks_formatted.jsonl"
        with open(chunks_out, "w", encoding="utf-8") as f:
            for item in formatted_chunks:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        # 4-2. Concept 기반 결과물 저장
        concepts_out = output_dir / f"{day}_concepts_formatted.jsonl"
        with open(concepts_out, "w", encoding="utf-8") as f:
            for item in formatted_concepts:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return len(formatted_chunks), len(formatted_concepts)

def main():
    parser = argparse.ArgumentParser(description="Step 05: Formatter (Chunk & Concept JSON Formatter)")
    parser.add_argument("--input_type", type=str, choices=["base_cleaned", "gemini_cleaned"], default="base_cleaned")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent.parent
    
    # 3단계(Chunks)와 4단계(Propositions)의 결과를 불러옵니다.
    chunks_dir = base_dir / "data" / "phase3_chunks" / args.input_type
    props_dir  = base_dir / "data" / "phase4_propositions" / args.input_type
    output_dir = base_dir / "data" / "phase5_formatted" / args.input_type
    
    if not chunks_dir.exists() or not props_dir.exists():
        print(f"[ERROR] Required input directories not found for {args.input_type}.")
        print("Please ensure Phase 3 and Phase 4 have been executed.")
        return

    formatter = Formatter()
    jsonl_files = sorted(chunks_dir.glob("*.jsonl"))
    
    if not jsonl_files:
        print("[ERROR] No chunk files found!")
        return

    total_chunks = 0
    total_concepts = 0
    files_proc = 0

    print("=== Phase 5: Formatting Data ===")
    for chunk_file in jsonl_files:
        prop_file = props_dir / chunk_file.name
        
        if not prop_file.exists():
            print(f"[Warning] Proposition file missing for {chunk_file.name}, formatting incomplete chunk.")
            
        c_count, p_count = formatter.format_documents(chunk_file, prop_file, output_dir)
        total_chunks += c_count
        total_concepts += p_count
        files_proc += 1
        
        print(f"  [OK] {chunk_file.name} -> Chunk Docs: {c_count}, Concept Docs: {p_count}")

    print(f"\n{'='*60}")
    print(f"[Phase 5 전체 출력 통계 ({args.input_type})]")
    print(f"  병합 처리된 파일: {files_proc}개")
    print(f"  생성된 Chunk DB:   {total_chunks}건")
    print(f"  생성된 Concept DB: {total_concepts}건")
    print(f"  저장 경로: {output_dir}")

if __name__ == "__main__":
    main()
