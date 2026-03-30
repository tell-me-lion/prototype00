import { useState } from 'react'
import type { Lecture } from '../types/models'

interface ActivityHeatmapProps {
  lectures: Lecture[]
}

function getWeekDays(weeksBack: number): Date[] {
  const days: Date[] = []
  const today = new Date()
  // 이번 주 일요일 기준으로 시작
  const currentDay = today.getDay()
  const startDate = new Date(today)
  startDate.setDate(today.getDate() - currentDay - (weeksBack - 1) * 7)

  for (let i = 0; i < weeksBack * 7; i++) {
    const d = new Date(startDate)
    d.setDate(startDate.getDate() + i)
    if (d <= today) days.push(d)
  }
  return days
}

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

export function ActivityHeatmap({ lectures }: ActivityHeatmapProps) {
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)

  // 날짜별 완료 강의 수 집계
  const countMap = new Map<string, number>()
  lectures.forEach((l) => {
    if (l.status === 'completed') {
      const key = l.date
      countMap.set(key, (countMap.get(key) ?? 0) + 1)
    }
  })

  const days = getWeekDays(8)

  // 주 단위로 그룹 (열 = 주, 행 = 요일)
  const weeks: Date[][] = []
  let currentWeek: Date[] = []
  days.forEach((d) => {
    if (d.getDay() === 0 && currentWeek.length > 0) {
      weeks.push(currentWeek)
      currentWeek = []
    }
    currentWeek.push(d)
  })
  if (currentWeek.length > 0) weeks.push(currentWeek)

  function getLevel(count: number): number {
    if (count === 0) return 0
    if (count === 1) return 1
    if (count === 2) return 2
    return 3
  }

  const handleMouseEnter = (e: React.MouseEvent, d: Date, count: number) => {
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    const parent = (e.target as HTMLElement).closest('.tml-heatmap')?.getBoundingClientRect()
    if (!parent) return
    setTooltip({
      text: `${formatDate(d)} — ${count > 0 ? `${count}개 분석` : '활동 없음'}`,
      x: rect.left - parent.left + rect.width / 2,
      y: rect.top - parent.top - 8,
    })
  }

  return (
    <div className="tml-heatmap" style={{ position: 'relative' }}>
      {tooltip && (
        <div
          className="tml-heatmap__tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
      <div className="tml-heatmap__grid">
        {/* 요일 레이블 */}
        <div className="tml-heatmap__labels">
          {DAY_LABELS.map((label, i) => (
            <span key={i} className="tml-heatmap__day-label">
              {i % 2 === 1 ? label : ''}
            </span>
          ))}
        </div>
        {/* 셀 그리드 */}
        <div className="tml-heatmap__weeks">
          {weeks.map((week, wi) => (
            <div key={wi} className="tml-heatmap__week-col">
              {/* 첫 주의 빈 셀 패딩 */}
              {wi === 0 && Array.from({ length: week[0].getDay() }).map((_, i) => (
                <div key={`pad-${i}`} className="tml-heatmap__cell tml-heatmap__cell--empty" />
              ))}
              {week.map((d, di) => {
                const count = countMap.get(formatDate(d)) ?? 0
                const level = getLevel(count)
                return (
                  <div
                    key={di}
                    className={`tml-heatmap__cell tml-heatmap__cell--level-${level}`}
                    style={{ animationDelay: `${(wi * 7 + di) * 20}ms` }}
                    onMouseEnter={(e) => handleMouseEnter(e, d, count)}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
      {/* 범례 */}
      <div className="tml-heatmap__legend">
        <span className="tml-heatmap__legend-label">적음</span>
        {[0, 1, 2, 3].map((level) => (
          <div key={level} className={`tml-heatmap__cell tml-heatmap__cell--level-${level} tml-heatmap__cell--no-anim`} />
        ))}
        <span className="tml-heatmap__legend-label">많음</span>
      </div>
    </div>
  )
}
