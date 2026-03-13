"""
Step 01: 정규식 기반 1차 클렌징
- 타임스탬프를 메타데이터로 보존, 화자 ID 제거
- 인접 라인 병합 (15초 이내), 세션 자동 감지 (30분 gap)
- 불용어 제거, STT 오인식 보정
- 출력: pipeline/01_cleaned/{날짜}.jsonl
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import timedelta

# Windows cp949 인코딩 문제 방지
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ── 경로 설정 ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "donotuploadthis" / "강의 스크립트"
OUTPUT_DIR = ROOT / "pipeline" / "01_cleaned"
CONFIG_DIR = ROOT / "pipeline" / "config"


# ── 정규식 패턴 ────────────────────────────────────────
LINE_PATTERN = re.compile(
    r"^<(\d{2}):(\d{2}):(\d{2})>\s+[a-f0-9]+:\s*(.*)$"
)


def load_config():
    """불용어 사전과 STT 보정 사전 로드"""
    with open(CONFIG_DIR / "stopwords.json", "r", encoding="utf-8") as f:
        stopwords = json.load(f)
    with open(CONFIG_DIR / "stt_corrections.json", "r", encoding="utf-8") as f:
        corrections = json.load(f)
    return stopwords, corrections


def parse_time(h: str, m: str, s: str) -> timedelta:
    """시:분:초 → timedelta"""
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s))


def format_time(td: timedelta) -> str:
    """timedelta → HH:MM:SS 문자열"""
    total = int(td.total_seconds())
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def parse_lines(filepath: Path) -> list[dict]:
    """원본 파일에서 (time, text) 라인 목록 추출"""
    lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            match = LINE_PATTERN.match(raw)
            if match:
                h, m, s, text = match.groups()
                text = text.strip()
                if text:
                    lines.append({
                        "time": parse_time(h, m, s),
                        "text": text,
                    })
    return lines


def apply_stt_corrections(text: str, corrections: dict) -> str:
    """STT 오인식 보정 (제거 + 교체)"""
    # 먼저 제거 (긴 것부터)
    for removal in sorted(corrections.get("removals", []), key=len, reverse=True):
        text = text.replace(removal, "")

    # 교체 (긴 키부터 — 부분 매칭 문제 방지)
    replacements = corrections.get("replacements", {})
    for wrong in sorted(replacements.keys(), key=len, reverse=True):
        text = text.replace(wrong, replacements[wrong])

    # 다중 공백 정리
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def is_stopword(text: str, stopwords: dict) -> bool:
    """불용어 판별"""
    stripped = text.strip().rstrip(".")

    # 완전 매칭
    if stripped in stopwords.get("exact_match", []):
        return True
    if text.strip() in stopwords.get("exact_match", []):
        return True

    # 시작 패턴 (너무 짧은 문장이 이 패턴으로 시작하면 DROP)
    # startswith는 너무 공격적이므로 짧은 문장에만 적용
    if len(text.strip()) < 15:
        for prefix in stopwords.get("startswith", []):
            if text.strip().startswith(prefix):
                return True

    # 최소 길이
    min_len = stopwords.get("min_char_length", 5)
    if len(stripped) < min_len:
        return True

    return False


def merge_lines(lines: list[dict], max_gap_sec: int = 15) -> list[dict]:
    """인접 라인 병합 (같은 세션 내, 시간 간격 ≤ max_gap_sec)"""
    if not lines:
        return []

    paragraphs = []
    current = {
        "time": lines[0]["time"],
        "texts": [lines[0]["text"]],
    }

    for line in lines[1:]:
        gap = (line["time"] - current["time"]).total_seconds()
        # 같은 단락으로 병합 (gap이 음수인 경우도 허용 — 같은 초에 여러 라인)
        if 0 <= gap <= max_gap_sec:
            current["texts"].append(line["text"])
        else:
            paragraphs.append({
                "time": current["time"],
                "text": " ".join(current["texts"]),
            })
            current = {
                "time": line["time"],
                "texts": [line["text"]],
            }

    # 마지막 단락
    paragraphs.append({
        "time": current["time"],
        "text": " ".join(current["texts"]),
    })

    return paragraphs


def detect_sessions(paragraphs: list[dict], session_gap_min: int = 30) -> list[dict]:
    """세션 자동 감지 (시간 gap ≥ session_gap_min분이면 새 세션)"""
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


def extract_date(filename: str) -> str:
    """파일명에서 날짜 추출: 2026-02-02_kdt-... → 2026-02-02"""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else filename.replace(".txt", "")


def process_file(filepath: Path, stopwords: dict, corrections: dict) -> list[dict]:
    """단일 파일 처리 → 클렌징된 단락 리스트"""
    day = extract_date(filepath.name)

    # 1) 라인 파싱
    lines = parse_lines(filepath)
    stats = {"raw_lines": len(lines)}

    # 2) STT 보정
    for line in lines:
        line["text"] = apply_stt_corrections(line["text"], corrections)

    # 3) 불용어 제거
    lines = [l for l in lines if not is_stopword(l["text"], stopwords)]
    stats["after_stopword"] = len(lines)

    # 4) 인접 라인 병합
    paragraphs = merge_lines(lines)
    stats["paragraphs"] = len(paragraphs)

    # 5) 세션 감지
    paragraphs = detect_sessions(paragraphs)

    # 6) 출력 포맷
    result = []
    for para in paragraphs:
        text = para["text"].strip()
        if not text:
            continue
        result.append({
            "day": day,
            "session": para["session"],
            "time": format_time(para["time"]),
            "paragraph": text,
        })

    stats["output_paragraphs"] = len(result)
    return result, stats


def main():
    parser = argparse.ArgumentParser(description="Step 01: 정규식 기반 1차 클렌징")
    parser.add_argument("--input-dir", type=str, default=str(INPUT_DIR))
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stopwords, corrections = load_config()

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"[ERROR] No .txt files found in '{input_dir}'")
        return

    total_stats = {
        "files": 0,
        "raw_lines": 0,
        "after_stopword": 0,
        "paragraphs": 0,
        "output_paragraphs": 0,
    }

    for filepath in txt_files:
        day = extract_date(filepath.name)
        result, stats = process_file(filepath, stopwords, corrections)

        # JSONL 출력
        out_path = output_dir / f"{day}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in result:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # 통계 집계
        total_stats["files"] += 1
        for k in ["raw_lines", "after_stopword", "paragraphs", "output_paragraphs"]:
            total_stats[k] += stats[k]

        sessions = set(r["session"] for r in result)
        print(f"  [OK] {filepath.name} -> {out_path.name}  "
              f"(line {stats['raw_lines']} -> para {stats['output_paragraphs']}, "
              f"session {len(sessions)})")

    print(f"\n{'='*60}")
    print(f"[전체 통계]")
    print(f"  파일 수:        {total_stats['files']}")
    print(f"  원본 라인:      {total_stats['raw_lines']}")
    print(f"  불용어 제거 후: {total_stats['after_stopword']}")
    print(f"  병합 단락:      {total_stats['paragraphs']}")
    print(f"  최종 출력:      {total_stats['output_paragraphs']}")
    print(f"  제거율:         {(1 - total_stats['output_paragraphs']/max(total_stats['raw_lines'],1))*100:.1f}%")


if __name__ == "__main__":
    main()
