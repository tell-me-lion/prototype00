import os
import json
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
warnings.filterwarnings('ignore') # TF-IDF 경고 등 무시

class SemanticChunker:
    def __init__(self, model_name="jhgan/ko-sroberta-multitask", threshold=0.40, max_sentences=15):
        # 한국어 텍스트 문장 임베딩에 성능이 좋은 SRoBERTa 모델
        print(f"[Model Load] 임베딩 모델 '{model_name}' 로드 중...")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.max_sentences = max_sentences

    def chunk_sentences(self, sentences: list[dict]) -> list[dict]:
        """세션 단위의 문장 리스트를 의미 기반 청크로 분리"""
        if not sentences:
            return []
            
        texts = [s["text"] for s in sentences]
        # 문장 전체 임베딩
        embeddings = self.model.encode(texts)
        
        chunks = []
        current_chunk = [sentences[0]]
        current_embeds = [embeddings[0]]
        
        for i in range(1, len(sentences)):
            # 병합 중인 현재 청크의 평균 벡터와 다음 문장 간의 유사도
            chunk_embed = np.mean(current_embeds, axis=0)
            sim = cosine_similarity([chunk_embed], [embeddings[i]])[0][0]
            
            # 유사도가 임계치보다 떨어지거나(문맥전환 방어선), 청크가 너무 길어지면 새 청크로 분리
            if sim < self.threshold or len(current_chunk) >= self.max_sentences:
                chunks.append(current_chunk)
                current_chunk = [sentences[i]]
                current_embeds = [embeddings[i]]
            else:
                current_chunk.append(sentences[i])
                current_embeds.append(embeddings[i])
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def compute_tfidf(self, chunks_data: list[dict]):
        """강의 1개(파일) 전체 코퍼스 내 TF-IDF를 계산하고 상위 키워드를 각 청크에 부여"""
        # 정규식을 이용해 너무 짧은 글자나 의미 없는 기호 제외 (명사 위주 추출 지향)
        corpus = [c["text"] for c in chunks_data]
        if not corpus or len(corpus) < 2:
            for chunk in chunks_data:
                chunk["keywords"] = []
                chunk["tfidf_scores"] = {}
            return
            
        # max_df: 85% 이상 문서를 차지하는 단어는 불용어로 처리
        vectorizer = TfidfVectorizer(max_df=0.85, min_df=1) 
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            
            for i, chunk in enumerate(chunks_data):
                row = tfidf_matrix.getrow(i).toarray()[0]
                # 점수 높은 상위 5개 추출
                top_indices = row.argsort()[-5:][::-1]
                
                keywords = []
                tfidf_scores = {}
                for idx in top_indices:
                    score = float(row[idx])
                    if score > 0.1: # 유의미한 점수만 저장
                        word = feature_names[idx]
                        keywords.append(word)
                        tfidf_scores[word] = round(score, 3)
                        
                chunk["keywords"] = keywords
                chunk["tfidf_scores"] = tfidf_scores
        except ValueError:
            for chunk in chunks_data:
                chunk["keywords"] = []
                chunk["tfidf_scores"] = {}

    def process_file(self, filepath: Path, output_dir: Path) -> dict:
        day = filepath.stem
        sentences = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    sentences.append(json.loads(line))
        
        if not sentences:
            return {"input_sents": 0, "output_chunks": 0}
            
        # 세션별로 문장 먼저 그룹화 (서로 다른 세션을 억지로 이어붙이는 것 방지)
        sessions = {}
        for s in sentences:
            sid = s.get("session", 1)
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(s)
            
        all_chunks = []
        chunk_counter = 1
        
        # 세션 각각에 대해 시맨틱 청킹 수행
        for sid, sents in tqdm(sessions.items(), desc=f"  [임베딩 청킹] {filepath.name}", leave=False):
            chunked_lists = self.chunk_sentences(sents)
            
            for chunk_sents in chunked_lists:
                combined_text = " ".join([s["text"] for s in chunk_sents])
                sent_ids = [s["sent_id"] for s in chunk_sents]
                
                base_time = chunk_sents[0].get("time", "")
                # 원본 파일명 보존
                source_f = chunk_sents[0].get("source_file", filepath.name)
                
                chunk_id = f"{day}_S{sid:02d}_C{chunk_counter:03d}"
                
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "session_id": sid,
                    "sent_ids": sent_ids,
                    "time": base_time,
                    "text": combined_text,
                    "meta": {
                        "source_file": source_f,
                        "sentence_count": len(chunk_sents)
                    }
                })
                chunk_counter += 1
                
        # 문서 단위로 TF-IDF 키워드 추출하여 병합
        self.compute_tfidf(all_chunks)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in all_chunks:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return {"input_sents": len(sentences), "output_chunks": len(all_chunks)}

def main():
    parser = argparse.ArgumentParser(description="Step 03: Semantic Chunker & TF-IDF Extraction")
    parser.add_argument("--input_type", type=str, choices=["base_cleaned", "gemini_cleaned"], default="base_cleaned")
    # 유사도 임계치: 실험해보고 싶을 때 조절 (기본값 0.40은 한국어 SRoBERTa에서 준수한 성능)
    parser.add_argument("--threshold", type=float, default=0.40, help="문맥 전환 판단을 위한 코사인 유사도 기준점")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent.parent
    
    input_dir = base_dir / "data" / "phase2_sentences" / args.input_type
    output_dir = base_dir / "data" / "phase3_chunks" / args.input_type
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        return

    chunker = SemanticChunker(threshold=args.threshold)
    
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[ERROR] Phase 2 결과가 없습니다.")
        return

    total_stats = {"files": 0, "input_sents": 0, "output_chunks": 0}

    for filepath in jsonl_files:
        print(f"Processing {filepath.name}...")
        stats = chunker.process_file(filepath, output_dir)
        
        total_stats["files"] += 1
        total_stats["input_sents"] += stats["input_sents"]
        total_stats["output_chunks"] += stats["output_chunks"]

        print(f"  [OK] {filepath.name} (sent {stats['input_sents']} -> chunk {stats['output_chunks']})")

    print(f"\n{'='*60}")
    print(f"[Phase 3 전체 통계 ({args.input_type})]")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 문장 수:   {total_stats['input_sents']}")
    print(f"  시맨틱 청크 수: {total_stats['output_chunks']}")

if __name__ == "__main__":
    main()
