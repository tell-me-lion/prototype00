import { useNavigate } from 'react-router-dom'
import type { Lecture } from '../types/models'

interface ConceptCloudProps {
  lectures: Lecture[]
}

interface ConceptEntry {
  text: string
  importance: number
  lectureId: string
}

export function ConceptCloud({ lectures }: ConceptCloudProps) {
  const navigate = useNavigate()

  // 완료된 강의의 result_summary에서 개념 데이터 파생
  // 현재 API에 concepts 목록이 없으므로 course_name + meta에서 키워드 추출
  // → 더미로 강의명 기반 태그 생성
  const completedLectures = lectures.filter((l) => l.status === 'completed')

  if (completedLectures.length === 0) return null

  // 강의명에서 키워드 추출 (간단한 파싱)
  const concepts: ConceptEntry[] = completedLectures.flatMap((l) => {
    const words = l.course_name
      .split(/[\s·,—\-()（）]+/)
      .filter((w) => w.length >= 2)
    return words.map((w, i) => ({
      text: w,
      importance: Math.max(0.4, 1 - i * 0.15),
      lectureId: l.lecture_id,
    }))
  })

  // 중복 제거 (같은 텍스트면 importance 높은 것 유지)
  const uniqueMap = new Map<string, ConceptEntry>()
  concepts.forEach((c) => {
    const existing = uniqueMap.get(c.text)
    if (!existing || c.importance > existing.importance) {
      uniqueMap.set(c.text, c)
    }
  })
  const uniqueConcepts = Array.from(uniqueMap.values()).slice(0, 16)

  // importance에 따른 폰트 크기 (0.75rem ~ 1.25rem)
  function getFontSize(importance: number): string {
    const min = 0.75
    const max = 1.25
    return `${min + importance * (max - min)}rem`
  }

  return (
    <div className="tml-concept-cloud">
      {uniqueConcepts.map((c, i) => (
        <button
          key={`${c.text}-${i}`}
          className="tml-concept-cloud__tag"
          style={{
            fontSize: getFontSize(c.importance),
            animationDelay: `${i * 50}ms`,
          }}
          onClick={() => navigate(`/lecture/${c.lectureId}`)}
        >
          {c.text}
        </button>
      ))}
    </div>
  )
}
