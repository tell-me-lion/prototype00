# DESIGN.md — 알려주사자 프론트엔드 디자인 가이드

---

## 1. Design Thinking

### Purpose
강의 녹화본에서 핵심 개념·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 서비스.
사용자는 멋쟁이사자처럼 수강생 — 실용적인 개발자 지망생.

### 핵심 UX 원칙 — "유저가 편할 수 있도록"

유저는 파일을 업로드하지 않는다. 대시보드에 강의 목록이 떠 있고, 원하는 강의를 선택하면 끝.

| 기존 (❌) | 변경 후 (✅) |
|-----------|-------------|
| 유저가 `.txt` 파일 직접 업로드 | 대시보드에서 강의 선택 → "가져오기" 클릭 |
| 드래그 앤 드롭 업로드 영역 | 강의 카드 목록 + 선택 UI |
| 업로드 → 대기 → 결과 | 선택 → 처리 중 상태 → 결과 자동 표시 |

### Tone — "Knowledge Dashboard"

데이터가 정제되어 시각적으로 펼쳐지는 인텔리전스 플랫폼.
Notion처럼 조용하지 않고, Pitch처럼 색이 살아있다.
그러나 과하지 않다 — 오렌지와 네이비가 구조를 잡고, 여백이 숨을 쉬게 한다.

### Constraints
- React + TypeScript + Tailwind CSS
- 한국어 텍스트 비중 높음 → 한글 폰트 가독성 필수
- 라이트 테마 기본, 다크 테마 선택
- `prefers-reduced-motion`, `prefers-color-scheme` 대응

### Differentiation — 하나만 기억한다면?

> **"멋쟁이사자처럼 오렌지가 네이비 위에 정확하게 찍힌다 — 공부 앱이 아니라 대시보드 같다"**

한국 에듀테크에서 이 조합을 쓰는 곳은 없다.

---

## 2. 색상 시스템

```css
:root {
  /* === 브랜드 === */
  --tml-orange:         #FF6B00;   /* 멋쟁이사자처럼 오렌지 (프라이머리) */
  --tml-orange-light:   #FFF0E6;   /* 오렌지 배경 (연함) */
  --tml-orange-dark:    #CC5500;   /* 오렌지 호버/강조 */

  --tml-navy:           #0F1F3D;   /* 딥 네이비 (세컨더리) */
  --tml-navy-mid:       #1E3A5F;   /* 네이비 미드 (카드 헤더 등) */
  --tml-navy-light:     #EBF0F8;   /* 네이비 배경 (연함) */

  /* === 라이트 테마 (기본) === */
  --tml-bg:             #FFFFFF;
  --tml-bg-raised:      #F6F8FB;   /* 카드/패널 */
  --tml-bg-overlay:     #EDF1F7;   /* 호버, 선택 */

  --tml-ink:            #0F1F3D;   /* 주 텍스트 (네이비) */
  --tml-ink-secondary:  #3D556E;   /* 본문 보조 */
  --tml-ink-muted:      #7A92A8;   /* 라벨, 메타 */

  --tml-rule:           #DDE3EC;   /* 구분선 */
  --tml-rule-strong:    #B8C5D4;   /* 굵은 구분선 */

  --tml-quiz-fill:      #4D7FA8;   /* 빈칸채우기 퀴즈 세로 바 */
  --tml-quiz-code:      #2D6A4F;   /* 코드실행형 퀴즈 세로 바 */

  --tml-white:          #FFFFFF;   /* 버튼 텍스트 등 고정 흰색 */
}

[data-theme="dark"] {
  --tml-bg:             #0A1628;
  --tml-bg-raised:      #111E33;
  --tml-bg-overlay:     #1A2D4A;

  --tml-ink:            #E8EDF5;
  --tml-ink-secondary:  #9DB4CC;
  --tml-ink-muted:      #4D6B85;

  --tml-orange-light:   #2A1800;
  --tml-navy-light:     #0A1628;

  --tml-rule:           #1E3050;
  --tml-rule-strong:    #2A4068;

  --tml-quiz-fill:      #6A9FBF;   /* 다크에서 더 밝게 */
  --tml-quiz-code:      #4A9A6F;
}
```

### 컬러 용도 매핑

| 색상 | 사용처 |
|------|--------|
| `--tml-orange` | CTA 버튼, 활성 탭 언더라인, 개념 카드 좌측 바, 로고 액센트 |
| `--tml-navy` | 헤더 배경, 뱃지 배경, 섹션 제목 |
| `--tml-navy-mid` | 퀴즈 타입 배지, 주차 탭 배경 |
| `--tml-orange-light` | 오렌지 액센트 배경 (태그, 칩) |
| `--tml-navy-light` | 네이비 액센트 배경 (학습포인트 배지) |

---

## 3. 타이포그래피

### 폰트 선택

| 역할 | 폰트 | 선택 이유 |
|------|------|----------|
| 영문 헤딩/디스플레이 | **Syne** | 기하학적이고 대담함. 일반 산세리프와 다른 개성. 플랫폼 느낌에 최적 |
| 한글 전체 | **Pretendard** | 한글 UI 최적화, 웨이트 범위 넓음, 모던하고 읽기 편함 |
| 영문 본문/UI | **IBM Plex Sans** | 전문적이고 기술적. Syne 헤딩과 무게 균형 |
| 수치/코드/ID | **IBM Plex Mono** | IBM Plex 패밀리 통일, 정밀하고 깔끔 |

```css
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css');

:root {
  --font-display: 'Syne', 'Pretendard Variable', 'Pretendard', sans-serif;
  --font-body:    'IBM Plex Sans', 'Pretendard Variable', 'Pretendard', sans-serif;
  --font-mono:    'IBM Plex Mono', 'JetBrains Mono', monospace;
}
```

### 타입 스케일

| 용도 | 폰트 | 크기 | 굵기 | 특이사항 |
|------|------|------|------|---------|
| 페이지 제목 (h1) | Syne | 2rem | 700 | `letter-spacing: -0.02em` |
| 섹션 제목 (h2) | Syne | 1.25rem | 600 | `letter-spacing: -0.01em` |
| 카드 제목 | Pretendard | 0.9375rem | 600 | — |
| 카드 레이블 | IBM Plex Sans | 0.6875rem | 600 | `uppercase + letter-spacing: 0.08em` |
| 본문 | Pretendard | 0.875rem | 400 | `line-height: 1.7` |
| 수치/ID | IBM Plex Mono | 0.75rem | 400 | 고정폭, muted 색상 |

---

## 4. 공간 구성

- **최대 너비 `1120px`**, 좌우 패딩 `px-8 sm:px-12`
- 메인 콘텐츠 : 사이드 패널 = **5 : 3** 비율
- **카드는 세로 스택** — 격자 배열 대신 정보 흐름 우선
- 헤더: 좌측 정렬, 절대 중앙 정렬 없음
- 섹션 간 구분: `border-top` + 섹션 레이블 (대문자, muted)
- 카드 간격: `gap-3` (밀도감 유지)

---

## 5. 컴포넌트 스펙

### 기본 카드 (`.tml-card`)

```css
.tml-card {
  background: var(--tml-bg-raised);
  border: 1px solid var(--tml-rule);
  border-radius: 6px;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.tml-card:hover {
  background: var(--tml-bg-overlay);
  border-color: var(--tml-rule-strong);
  box-shadow: 0 2px 8px rgba(15, 31, 61, 0.06);
}
```

### 강의 카드 (대시보드용)

대시보드에서 강의를 선택하는 카드. 기본 카드를 확장한다.

```
┌──────────────────────────────────────────────┐
│  📅 2026-03-25                    Week 12    │
│  데이터베이스 설계 — 정규화와 반정규화        │
│  ─────────────────────────────────────────   │
│  처리 상태: ✅ 완료  |  개념 12개  퀴즈 8개   │
│                              [결과 보기 →]   │
└──────────────────────────────────────────────┘
```

| 상태 | 표시 |
|------|------|
| 미처리 | muted 텍스트 + "가져오기" 버튼 |
| 처리 중 | 오렌지 shimmer 프로그레스 |
| 완료 | 결과 요약 + "결과 보기" 링크 |

### 핵심 개념 카드

왼쪽 오렌지 세로 바 + Syne 개념명 + 모노스페이스 중요도.

```
┌──────────────────────────────────────────────┐
│▌ 강화학습 (Reinforcement Learning)    ×0.87  │
│  Week 3 · lec_015          [개념] [ML]       │
└──────────────────────────────────────────────┘
  ↑ 오렌지 3px 세로선
```

```css
.concept-bar   { width: 3px; background: var(--tml-orange); border-radius: 2px; }
.concept-name  { font-family: var(--font-display); font-weight: 600; }
.concept-score { font-family: var(--font-mono); color: var(--tml-ink-muted); }
```

### 퀴즈 카드

타입별 좌측 세로선 색상 + 네이비 뱃지.

| 타입 | 세로선 |
|------|--------|
| `mcq` | `var(--tml-orange)` |
| `short` | `var(--tml-navy-mid)` |
| `fill` | `var(--tml-quiz-fill)` |
| `code` | `var(--tml-quiz-code)` |

```
┌───────────────────────────────────────────┐
│▌ [MCQ]                            Q-003   │
│  "다음 중 강화학습의 핵심 요소는?"          │
└───────────────────────────────────────────┘
```

### 네비게이션 헤더

```
┌──────────────────────────────────────────────────────────┐
│  ● 알려주사자        홈   단일강의   주차별가이드      ◑  │
├──────────────────────────────────────────────────────────┤  ← 1px rule
```

- 배경: `var(--tml-bg)` — 투명/blur 없음
- 로고: Syne 700 + 오렌지 도트 `●`
- 활성 탭: 오렌지 하단 언더라인 2px
- 다크/라이트 토글: 우측 `◑` 아이콘
- 높이: `56px`

### 뱃지 / 태그

```css
.badge-orange {
  background: var(--tml-orange-light);
  color: var(--tml-orange-dark);
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.badge-navy {
  background: var(--tml-navy-light);
  color: var(--tml-navy-mid);
}
```

### CTA 버튼

```css
.btn-primary {
  background: var(--tml-orange);
  color: var(--tml-white);
  font-weight: 600;
  border-radius: 6px;
  padding: 8px 20px;
  transition: background 0.15s ease, transform 0.1s ease;
}
.btn-primary:hover {
  background: var(--tml-orange-dark);
  transform: translateY(-1px);
}
```

### 처리 상태 인디케이터

강의 처리 진행 상황을 보여주는 컴포넌트.

| 상태 | 시각 표현 |
|------|----------|
| 대기 중 | muted 텍스트, 점선 테두리 |
| STT 변환 중 | 오렌지 shimmer 프로그레스 바 (1단계) |
| 전처리 중 | 오렌지 shimmer 프로그레스 바 (2단계) |
| 분석 완료 | 체크마크 + 결과 요약 |
| 오류 | 빨간 좌측 세로선 + 오류 메시지 |

---

## 6. 배경 & 시각 디테일

### 서브틀 노이즈 그레인 (종이 질감, 강도 낮음)

```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  background-size: 200px 200px;
  opacity: 0.5;
}
```

### 오렌지 액센트 글로우 (히어로 섹션 한정)

```css
.tml-hero-glow::before {
  content: '';
  position: absolute;
  top: -60px; right: 10%;
  width: 300px; height: 120px;
  background: radial-gradient(ellipse, rgba(255, 107, 0, 0.08), transparent 70%);
  pointer-events: none;
}
```

---

## 7. 모션

### 페이지 진입 — staggered rise

```css
@keyframes tml-rise {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.tml-animate {
  animation: tml-rise 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.tml-animate:nth-child(1) { animation-delay: 0ms; }
.tml-animate:nth-child(2) { animation-delay: 60ms; }
.tml-animate:nth-child(3) { animation-delay: 120ms; }
.tml-animate:nth-child(4) { animation-delay: 180ms; }
.tml-animate:nth-child(5) { animation-delay: 240ms; }

@media (prefers-reduced-motion: reduce) {
  .tml-animate { animation: none; }
}
```

### 상태 전환

| 상태 | 처리 |
|------|------|
| 로딩 | 펄스 스켈레톤 (오렌지 shimmer) |
| 에러 | 좌측 빨간 세로선 카드 |
| 호버 | `background` + `border-color` 강화, `box-shadow` |
| 탭 전환 | `opacity: 0 → 1` 0.2s |
| 처리 진행 | 프로그레스 바 단계별 채움 |
