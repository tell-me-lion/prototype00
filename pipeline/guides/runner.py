"""Guides 러너: 학습 가이드 및 핵심 요약 생성.

Mode B 전용. Phase 5 facts를 주차 단위로 집계하여 학습 가이드를 생성한다.
초안 구현 (주노) — 나중에 경현이 고도화하면 교체.
"""

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from pipeline import paths


def run_guides(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    week: int | None = None,
) -> None:
    """전처리 결과(Phase 5 Fact)만을 입력으로 주차별 학습 가이드를 생성.

    Mode B 전용. Mode A 출력(EP 개념, 퀴즈)을 읽지 않는다.

    Args:
        in_dir: phase5_facts 디렉터리. None이면 기본 경로.
        out_dir: 출력 디렉터리. None이면 기본 경로.
        week: 특정 주차만 처리. None이면 전체 주차.
    """
    src = in_dir or paths.DATA_PHASE5_FACTS
    dst = out_dir or paths.DATA_LEARNING_GUIDES
    dst.mkdir(parents=True, exist_ok=True)

    # first_date를 raw 디렉터리에서 산출 (catalog.py와 동일 기준)
    raw_dir = paths.DATA_RAW
    raw_dates: list[date] = []
    for txt_file in raw_dir.glob("*.txt"):
        d = _extract_date(txt_file.stem)
        if d is not None:
            raw_dates.append(d)
    if not raw_dates:
        print("[WARN] raw 디렉터리에 파일 없음 — first_date 산출 불가")
        return
    first_date = min(raw_dates)

    # Phase 5 facts 파일 수집
    dated_files: list[tuple[date, Path]] = []
    for jsonl_file in sorted(src.glob("*.jsonl")):
        file_date = _extract_date(jsonl_file.stem)
        if file_date is None:
            continue
        dated_files.append((file_date, jsonl_file))

    if not dated_files:
        print("[WARN] 날짜를 파싱할 수 있는 Phase 5 파일 없음")
        return

    # Phase 5 facts 파일을 주차별로 그룹핑
    week_chunks: dict[int, list[dict]] = defaultdict(list)

    for file_date, jsonl_file in dated_files:
        file_week = _calculate_week(file_date, first_date)
        if week is not None and file_week != week:
            continue

        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                week_chunks[file_week].append(chunk)
            except json.JSONDecodeError:
                continue

    if not week_chunks:
        target = f"week={week}" if week is not None else "전체"
        raise RuntimeError(f"처리할 주차 데이터 없음 (target={target}, phase5 파일={len(dated_files)}건, first_date={first_date})")

    # 주차별 가이드 생성
    for w, chunks in sorted(week_chunks.items()):
        guide = _build_guide(w, chunks)
        out_file = dst / f"week_{w:02d}.jsonl"
        with out_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps(guide, ensure_ascii=False) + "\n")
        print(f"[OK] week_{w:02d}.jsonl | {len(chunks)} chunks → guide 생성")


_DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _extract_date(stem: str) -> date | None:
    """파일명에서 날짜 추출. 예: '2026-02-11_kdt-backendj-21th' → date(2026, 2, 11)."""
    match = _DATE_PATTERN.match(stem)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _calculate_week(lecture_date: date, first_date: date) -> int:
    """첫 강의 날짜 기준 경과 일수로 주차 계산."""
    delta_days = (lecture_date - first_date).days
    return (delta_days // 7) + 1


def _build_guide(week: int, chunks: list[dict]) -> dict:
    """주차 데이터로 학습 가이드를 생성.

    초안 로직: facts에서 키워드 빈도 기반으로 핵심 개념 추출 + 요약 생성.
    """
    # 모든 facts 수집
    all_facts: list[str] = []
    for chunk in chunks:
        facts = chunk.get("facts", [])
        all_facts.extend(facts)

    # TF-IDF 키워드에서 핵심 개념 추출
    keyword_freq: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        tfidf = chunk.get("tfidf_scores", chunk.get("tfidf_keywords", {}))
        if isinstance(tfidf, dict):
            for kw, score in tfidf.items():
                if isinstance(score, (int, float)) and score > 0.05:
                    keyword_freq[kw] += 1
        elif isinstance(tfidf, list):
            for kw in tfidf:
                keyword_freq[str(kw)] += 1

    # 상위 10개 키워드를 핵심 개념으로
    top_concepts = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    key_concepts = [kw for kw, _ in top_concepts]

    # 요약: 핵심 facts 선별 (키워드 포함 + 긴 문장 우선)
    scored_facts = []
    for fact in all_facts:
        if len(fact) < 10:
            continue
        score = sum(1 for kw in key_concepts if kw.lower() in fact.lower())
        score += len(fact) / 200  # 긴 문장 보너스
        scored_facts.append((score, fact))

    scored_facts.sort(key=lambda x: x[0], reverse=True)
    summary_facts = [fact for _, fact in scored_facts[:5]]
    summary = f"{week}주차 핵심 학습 내용입니다.\n\n" + "\n".join(
        f"• {fact}" for fact in summary_facts
    )

    return {
        "week": week,
        "summary": summary,
        "key_concepts": key_concepts,
        "meta": {
            "source": "auto_generated",
            "total_chunks": len(chunks),
            "total_facts": len(all_facts),
        },
    }

