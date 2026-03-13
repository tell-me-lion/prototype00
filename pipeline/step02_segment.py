"""
Step 02: Kiwi 형태소 분석기 기반 문장 분리 + 필터링
- 1단계 출력(단락)을 논리적 문장으로 분리
- 품사 기반 필터링 (명사·동사 부족 문장 DROP)
- 중복 문장 제거
- 시간·세션 메타데이터 전달
- 출력: pipeline/02_sentences/{날짜}.jsonl
"""

import sys
import json

# Windows cp949 인코딩 문제 방지
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import argparse
from pathlib import Path
from collections import defaultdict

try:
    from kiwipiepy import Kiwi
except ImportError:
    print("[ERROR] kiwipiepy is not installed. Run: pip install kiwipiepy")
    raise SystemExit(1)


# ── 경로 설정 ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "pipeline" / "01_cleaned"
OUTPUT_DIR = ROOT / "pipeline" / "02_sentences"


# ── 품사 태그 분류 ─────────────────────────────────────
NOUN_TAGS = {"NNG", "NNP", "NNB"}  # 일반명사, 고유명사, 의존명사
VERB_TAGS = {"VV", "VA"}  # 동사, 형용사
INTERJ_TAGS = {"IC"}  # 감탄사
CONJ_TAGS = {"MAJ"}  # 접속부사


def init_kiwi() -> Kiwi:
    """Kiwi 형태소 분석기 초기화"""
    kiwi = Kiwi()
    # 도메인 용어 사전 등록
    domain_terms = [
        ("자바", "NNP"),
        ("MySQL", "NNP"),
        ("NIO", "NNP"),
        ("ANSI", "NNP"),
        ("SQL", "NNP"),
        ("InnoDB", "NNP"),
        ("B-tree", "NNP"),
        ("Oracle", "NNP"),
        ("PostgreSQL", "NNP"),
        ("NoSQL", "NNP"),
        ("OutputStream", "NNP"),
        ("BufferedReader", "NNP"),
        ("readLine", "NNP"),
        ("바이트", "NNG"),
        ("스트림", "NNG"),
        ("인코딩", "NNG"),
        ("디코딩", "NNG"),
        ("인덱스", "NNG"),
        ("파티션", "NNG"),
        ("프로시저", "NNG"),
        ("트리거", "NNG"),
        ("트랜잭션", "NNG"),
        ("조인", "NNG"),
        ("서브쿼리", "NNG"),
        ("데카르트", "NNP"),
        ("컬렉션", "NNG"),
        ("제네릭", "NNG"),
        ("이너조인", "NNG"),
        ("아우터조인", "NNG"),
        ("프라이머리키", "NNG"),
        ("유니크키", "NNG"),
        ("셀프조인", "NNG"),
        ("크로스조인", "NNG"),
    ]
    for word, tag in domain_terms:
        try:
            kiwi.add_user_word(word, tag)
        except Exception:
            pass  # 이미 등록 or 미지원 태그
    return kiwi


def should_drop(tokens: list, min_tokens: int = 3) -> bool:
    """품사 기반 필터링: DROP 여부 판단"""
    if len(tokens) <= min_tokens:
        return True

    tags = [t.tag for t in tokens]

    noun_count = sum(1 for t in tags if t in NOUN_TAGS)
    verb_count = sum(1 for t in tags if t in VERB_TAGS)

    # 명사·동사가 전혀 없으면 DROP
    if noun_count == 0 and verb_count == 0:
        return True

    # 감탄사+접속사 비율 >= 70% → DROP
    interj_conj = sum(1 for t in tags if t in INTERJ_TAGS | CONJ_TAGS)
    if len(tags) > 0 and interj_conj / len(tags) >= 0.7:
        return True

    return False


def normalize_for_dedup(text: str) -> str:
    """중복 비교용 정규화: 공백·구두점 제거, 소문자화"""
    import re
    text = re.sub(r"[^\w가-힣a-zA-Z0-9]", "", text)
    return text.lower()


def process_file(filepath: Path, kiwi: Kiwi) -> tuple[list[dict], dict]:
    """단일 파일 처리"""
    stats = {
        "input_paragraphs": 0,
        "total_sentences": 0,
        "dropped_sentences": 0,
        "dedup_removed": 0,
        "output_sentences": 0,
    }

    sentences = []
    seen_normalized = set()
    global_seq = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            para = json.loads(line)
            stats["input_paragraphs"] += 1

            day = para["day"]
            session = para["session"]
            time = para["time"]
            text = para["paragraph"]

            # Kiwi 문장 분리
            kiwi_sents = kiwi.split_into_sents(text)

            for sent_idx, sent in enumerate(kiwi_sents):
                sent_text = sent.text.strip()
                if not sent_text:
                    continue

                stats["total_sentences"] += 1

                # 형태소 분석
                tokens = kiwi.tokenize(sent_text)

                # 품사 기반 필터링
                if should_drop(tokens):
                    stats["dropped_sentences"] += 1
                    continue

                # 중복 제거
                norm = normalize_for_dedup(sent_text)
                if norm in seen_normalized:
                    stats["dedup_removed"] += 1
                    continue
                seen_normalized.add(norm)

                global_seq += 1

                # 단락 번호 + 문장 번호로 ID 생성
                day_compact = day.replace("-", "")
                para_idx = stats["input_paragraphs"]
                sent_id = f"{day_compact}-S{session}-P{para_idx:03d}-{sent_idx+1:02d}"

                # 주요 품사 태그만 추출
                pos_tags = [f"{t.form}/{t.tag}" for t in tokens
                            if t.tag in NOUN_TAGS | VERB_TAGS | {"NNP", "SL"}]

                sentences.append({
                    "id": sent_id,
                    "day": day,
                    "session": session,
                    "time": time,
                    "seq": global_seq,
                    "sentence": sent_text,
                    "pos_summary": pos_tags,
                })

    stats["output_sentences"] = len(sentences)
    return sentences, stats


def main():
    parser = argparse.ArgumentParser(description="Step 02: Kiwi 문장 분리 + 필터링")
    parser.add_argument("--input-dir", type=str, default=str(INPUT_DIR))
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[Step 02] Initializing Kiwi...")
    kiwi = init_kiwi()
    print("[Step 02] Ready\n")

    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[ERROR] No .jsonl files in '{input_dir}'. Run step01 first.")
        return

    total_stats = defaultdict(int)

    for filepath in jsonl_files:
        sentences, stats = process_file(filepath, kiwi)

        # JSONL 출력
        out_path = output_dir / filepath.name
        with open(out_path, "w", encoding="utf-8") as f:
            for item in sentences:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        for k, v in stats.items():
            total_stats[k] += v

        print(f"  [OK] {filepath.name} -> {out_path.name}  "
              f"(para {stats['input_paragraphs']} -> sent {stats['total_sentences']} "
              f"-> out {stats['output_sentences']}, "
              f"DROP {stats['dropped_sentences']}, dedup {stats['dedup_removed']})")

    print(f"\n{'='*60}")
    print(f"[전체 통계]")
    print(f"  입력 단락:      {total_stats['input_paragraphs']}")
    print(f"  전체 문장:      {total_stats['total_sentences']}")
    print(f"  품사 필터 DROP: {total_stats['dropped_sentences']}")
    print(f"  중복 제거:      {total_stats['dedup_removed']}")
    print(f"  최종 출력:      {total_stats['output_sentences']}")
    drop_rate = (1 - total_stats['output_sentences'] / max(total_stats['total_sentences'], 1)) * 100
    print(f"  축소율:         {drop_rate:.1f}%")


if __name__ == "__main__":
    main()
