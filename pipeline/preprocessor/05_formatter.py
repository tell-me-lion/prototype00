"""
Phase 5: 포매팅 (Formatter)
추출된 지식 명제(Phase 4)와 청크 원문/키워드(Phase 3)를 결합하여 RAG에 최적화된
구조화 JSON (ChunkDocument, ConceptDocument)으로 조립합니다.
"""
import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Any
from tqdm import tqdm

from pipeline import paths

class Formatter:
    def __init__(self) -> None:
        pass
        
    def resolve_session_label(self, time_str: str) -> str:
        """시작 시각 문자열(HH:MM:SS)로부터 오전/오후 세션 라벨을 결정"""
        if not time_str:
            return "Unknown"
        try:
            hour = int(time_str.split(":")[0])
            return "오전" if hour < 12 else "오후"
        except (ValueError, IndexError):
            return "Unknown"

    def format_documents(self, chunks_path: Path, props_path: Path, output_dir: Path) -> tuple[int, int]:
        # 1. 청크 데이터 로드 (Phase 3 결과물)
        chunks: dict[str, dict[str, Any]] = {}
        if chunks_path.exists():
            with open(chunks_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            c = json.loads(line)
                            chunks[c["chunk_id"]] = c
                        except json.JSONDecodeError:
                            continue
                        
        # 2. 명제 데이터 로드 및 해당 청크별 매핑 (Phase 4 결과물)
        chunk_facts: dict[str, list[dict[str, Any]]] = defaultdict(list)
        all_props: list[dict[str, Any]] = []
        if props_path.exists():
            with open(props_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            p = json.loads(line)
                            chunk_facts[p["chunk_id"]].append(p)
                            all_props.append(p)
                        except json.JSONDecodeError:
                            continue

        # 3. Chunk 문서(API 전송용/저장용) 구축
        formatted_chunks: list[dict[str, Any]] = []
        for cid, c in chunks.items():
            start_time = c.get("time", "")
            session_label = self.resolve_session_label(start_time)
            session_seq = c.get("session_id", 1)
            
            facts_list = [p["text"] for p in chunk_facts.get(cid, [])]
            
            formatted_chunks.append({
                "chunk_id": cid,
                "session": session_label,
                "session_seq": session_seq,
                "start_time": start_time,
                "text": c["text"],
                "facts": facts_list,
                "tfidf_keywords": c.get("keywords", [])
            })
            
        # 4. 요청하신 Concept DB 문서 구축 (주제별 그룹화)
        concepts_db: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "definition": set(),
            "related_concepts": set(),
            "source_chunk_ids": set()
        })
        
        for p in all_props:
            cid = p.get("chunk_id", "")
            candidates = p.get("concept_candidates", [])
            if not candidates:
                continue
                
            main_concept = candidates[0]
            concepts_db[main_concept]["definition"].add(p.get("text", ""))
            
            for cand in candidates[1:]:
                concepts_db[main_concept]["related_concepts"].add(cand)
            if cid in chunks:
                for kw in chunks[cid].get("keywords", []):
                    if kw != main_concept:
                        concepts_db[main_concept]["related_concepts"].add(kw)
                        
            concepts_db[main_concept]["source_chunk_ids"].add(cid)
            
        formatted_concepts: list[dict[str, Any]] = []
        for concept_name, data in concepts_db.items():
            defn = " / ".join(list(data["definition"]))
            concept_id = f"concept_{concept_name.lower().replace(' ', '_')}"
            
            formatted_concepts.append({
                "concept_id": concept_id,
                "concept": concept_name,
                "definition": defn,
                "related_concepts": list(data["related_concepts"])[:7], 
                "source_chunk_ids": list(data["source_chunk_ids"])
            })

        output_dir.mkdir(parents=True, exist_ok=True)
        day = chunks_path.stem
        
        chunks_out = output_dir / f"{day}_chunks_formatted.jsonl"
        with open(chunks_out, "w", encoding="utf-8") as f:
            for item in formatted_chunks:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        concepts_out = output_dir / f"{day}_concepts_formatted.jsonl"
        with open(concepts_out, "w", encoding="utf-8") as f:
            for item in formatted_concepts:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return len(formatted_chunks), len(formatted_concepts)

def main() -> None:
    parser = argparse.ArgumentParser(description="Step 05: Formatter (Chunk & Concept JSON Formatter)")
    args = parser.parse_args()

    chunks_dir = paths.DATA_PHASE3_CHUNKS
    props_dir  = paths.DATA_PHASE4_PROPOSITIONS
    output_dir = paths.DATA_PHASE5_FACTS
    
    if not chunks_dir.exists() or not props_dir.exists():
        print(f"[ERROR] Required input directories not found.")
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
    print(f"[Phase 5 전체 출력 통계]")
    print(f"  병합 처리된 파일: {files_proc}개")
    print(f"  생성된 Chunk DB:   {total_chunks}건")
    print(f"  생성된 Concept DB: {total_concepts}건")
    print(f"  저장 경로: {output_dir}")

if __name__ == "__main__":
    main()
