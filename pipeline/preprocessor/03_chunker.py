"""
Phase 3: 시맨틱 청킹 및 스코어링 (Semantic Chunker)
의미 기반으로 인접 문장 간의 문맥 전환 지점을 감지하여 청크(Chunk)로 분할하고, 
TF-IDF를 통해 핵심어를 추출합니다.
[옵션] --use_gemini_embed 플래그 적용 시 로컬 GPU(PyTorch) 대신 Gemini Embedding API를 사용합니다.
"""
import os
import json
import argparse
import time
import numpy as np
from pathlib import Path
from typing import Any
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# 배포 환경 대비: 로컬 GPU 모듈 지연 로딩
from pipeline import paths

warnings.filterwarnings('ignore')

class SemanticChunker:
    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask", 
                 threshold: float = 0.40, 
                 max_sentences: int = 15,
                 use_gemini_embed: bool = False) -> None:
        self.threshold = threshold
        self.max_sentences = max_sentences
        self.use_gemini_embed = use_gemini_embed
        
        if self.use_gemini_embed:
            print("[Model Load] GPU 의존성 제거 모드: Gemini API 임베딩 준비 중...")
            import google.genai as genai
            from google.genai import types
            from dotenv import load_dotenv
            load_dotenv(paths.ROOT / '.env')
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
            self.gemini_client = genai.Client(api_key=api_key)
            self.embed_model = "gemini-embedding-2-preview"
        else:
            print(f"[Model Load] 로컬 임베딩 모델 '{model_name}' 로드 중... (GPU/PyTorch 환경 권장)")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)

    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Gemini API 또는 로컬 SBERT를 통해 임베딩 벡터 목록을 반환.

        API 429 (rate limit) 발생 시 retryDelay를 준수하여 최대 3회 재시도.
        재시도 실패 시 RuntimeError를 발생시킨다 (0 벡터 폴백은 청킹을 무력화하므로 금지).
        """
        if self.use_gemini_embed:
            import re as _re
            all_embeddings = []
            max_retries = 3
            for i in range(0, len(texts), 90):
                batch_texts = texts[i:i+90]
                last_error = None
                for attempt in range(max_retries + 1):
                    try:
                        response = self.gemini_client.models.embed_content(
                            model=self.embed_model,
                            contents=batch_texts
                        )
                        time.sleep(0.5)
                        if hasattr(response, 'embeddings'):
                            all_embeddings.extend([emb.values for emb in response.embeddings])
                        else:
                            all_embeddings.append(response.embeddings.values)
                        break  # 성공 시 다음 배치로
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        # 429 rate limit: retryDelay 파싱 후 대기
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            delay_match = _re.search(r"retry(?:Delay)?['\"]?:\s*['\"]?(\d+\.?\d*)", err_str)
                            wait_sec = float(delay_match.group(1)) + 1.0 if delay_match else 15.0 * (attempt + 1)
                            print(f"[Gemini Embed] 429 rate limit — {wait_sec:.0f}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                            time.sleep(wait_sec)
                        elif "503" in err_str or "UNAVAILABLE" in err_str:
                            wait_sec = 10.0 * (2 ** attempt)
                            print(f"[Gemini Embed] 503 서비스 불가 — {wait_sec:.0f}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                            time.sleep(wait_sec)
                        else:
                            # 재시도 불가능한 에러
                            raise RuntimeError(f"임베딩 API 호출 실패 (재시도 불가): {e}") from e
                else:
                    # 재시도 모두 소진
                    raise RuntimeError(
                        f"임베딩 API 호출 {max_retries}회 재시도 후에도 실패: {last_error}"
                    )

            if len(all_embeddings) != len(texts):
                raise RuntimeError(
                    f"임베딩 결과 길이 불일치: texts={len(texts)}, embeds={len(all_embeddings)}"
                )
            return all_embeddings
        else:
            return self.model.encode(texts).tolist()

    def chunk_sentences(self, sentences: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """세션 단위의 문장 리스트를 의미 기반 청크로 분리"""
        if not sentences:
            return []
            
        texts = [s["text"] for s in sentences]
        embeddings = self._get_embeddings(texts)
        
        chunks: list[list[dict[str, Any]]] = []
        current_chunk = [sentences[0]]
        current_embeds = [embeddings[0]]
        
        for i in range(1, len(sentences)):
            chunk_embed = np.mean(current_embeds, axis=0)
            # 1D 배열을 2D 형태로 변환하여 cosine_similarity 계산
            sim = cosine_similarity([chunk_embed], [embeddings[i]])[0][0]
            
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

    def compute_tfidf(self, chunks_data: list[dict[str, Any]]) -> None:
        """강의 1개(파일) 전체 코퍼스 내 TF-IDF를 계산하고 상위 키워드를 각 청크에 부여"""
        # (TF-IDF는 scikit-learn 기반이므로 CPU에서 고속 동작. 변경 불필요)
        corpus = [c["text"] for c in chunks_data]
        if not corpus or len(corpus) < 2:
            for chunk in chunks_data:
                chunk["keywords"] = []
                chunk["tfidf_scores"] = {}
            return
            
        vectorizer = TfidfVectorizer(max_df=0.85, min_df=1) 
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            
            for i, chunk in enumerate(chunks_data):
                row = tfidf_matrix.getrow(i).toarray()[0]
                top_indices = row.argsort()[-5:][::-1]
                
                keywords = []
                tfidf_scores = {}
                for idx in top_indices:
                    score = float(row[idx])
                    if score > 0.1:
                        word = feature_names[idx]
                        keywords.append(word)
                        tfidf_scores[word] = round(score, 3)
                        
                chunk["keywords"] = keywords
                chunk["tfidf_scores"] = tfidf_scores
        except ValueError:
            for chunk in chunks_data:
                chunk["keywords"] = []
                chunk["tfidf_scores"] = {}

    def process_file(self, filepath: Path, output_dir: Path) -> dict[str, int]:
        day = filepath.stem
        sentences: list[dict[str, Any]] = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        sentences.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not sentences:
            return {"input_sents": 0, "output_chunks": 0}
            
        sessions: dict[int, list[dict[str, Any]]] = {}
        for s in sentences:
            sid = s.get("session", 1)
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(s)
            
        all_chunks: list[dict[str, Any]] = []
        chunk_counter = 1
        
        for sid, sents in tqdm(sessions.items(), desc=f"  [임베딩 청킹] {filepath.name}", leave=False):
            chunked_lists = self.chunk_sentences(sents)
            
            for chunk_sents in chunked_lists:
                combined_text = " ".join([s["text"] for s in chunk_sents])
                sent_ids = [s["sent_id"] for s in chunk_sents]
                
                base_time = chunk_sents[0].get("time", "")
                source_f = chunk_sents[0].get("source_file", filepath.name)
                proc_type = chunk_sents[0].get("processing_type", "base")
                
                chunk_id = f"{day}_S{sid:02d}_C{chunk_counter:03d}"
                
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "session_id": sid,
                    "sent_ids": sent_ids,
                    "time": base_time,
                    "text": combined_text,
                    "processing_type": proc_type,
                    "meta": {
                        "source_file": source_f,
                        "sentence_count": len(chunk_sents)
                    }
                })
                chunk_counter += 1
                
        self.compute_tfidf(all_chunks)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in all_chunks:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        return {"input_sents": len(sentences), "output_chunks": len(all_chunks)}

def main() -> None:
    parser = argparse.ArgumentParser(description="Step 03: Semantic Chunker (Local GPU or Gemini Cloud) & TF-IDF Extraction")
    parser.add_argument("--threshold", type=float, default=0.40, help="문맥 전환 판단을 위한 코사인 유사도 기준점")
    parser.add_argument("--use_gemini_embed", action="store_true", help="로컬 PyTorch 대신 Gemini Embedding API 사용")
    args = parser.parse_args()

    input_dir = paths.DATA_PHASE2_SENTENCES
    output_dir = paths.DATA_PHASE3_CHUNKS
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        return

    chunker = SemanticChunker(threshold=args.threshold, use_gemini_embed=args.use_gemini_embed)
    
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
    print(f"[Phase 3 전체 통계]")
    print(f"  API 모드:       {'Gemini' if args.use_gemini_embed else 'Local SROBERTa'}")
    print(f"  처리 파일 수:   {total_stats['files']}")
    print(f"  입력 문장 수:   {total_stats['input_sents']}")
    print(f"  시맨틱 청크 수: {total_stats['output_chunks']}")

if __name__ == "__main__":
    main()
