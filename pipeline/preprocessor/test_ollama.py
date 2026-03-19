import requests, json

payload = {
    "model": "gemma3:12b",
    "prompt": (
        "다음 텍스트에서 IT 지식 명제를 JSON 배열로 추출하세요.\n"
        '반드시 이 형식: [{"type": "definition", "concept": "...", "fact": "..."}]\n\n'
        "텍스트: 조인이란 두 개 이상의 테이블을 연결하여 데이터를 결합하는 방법입니다. "
        "내부 조인은 양쪽 테이블에서 일치하는 행만 반환합니다."
    ),
    "stream": False,
    "format": "json",
    "options": {"num_ctx": 4096, "num_gpu": 99}
}

print("Sending request to Ollama (gemma3:12b)...")
r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
d = r.json()

with open("test_ollama_result.json", "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

raw = d.get("response", "")
print(f"Response length: {len(raw)} chars")
print(f"Response:\n{raw}")

try:
    parsed = json.loads(raw)
    print(f"\n=== JSON PARSE: SUCCESS ===")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
except json.JSONDecodeError as e:
    print(f"\n=== JSON PARSE: FAILED === {e}")
