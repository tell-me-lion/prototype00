interface WeekTabProps {
  weeks: number[]
  activeWeek: number
  onSelect: (week: number) => void
}

export function WeekTab({ weeks, activeWeek, onSelect }: WeekTabProps) {
  return (
    <div className="tml-week-tabs">
      {weeks.map((week) => (
        <button
          key={week}
          className={`tml-week-tab${week === activeWeek ? ' tml-week-tab--active' : ''}`}
          onClick={() => onSelect(week)}
        >
          {week}주차
        </button>
      ))}
    </div>
  )
}
