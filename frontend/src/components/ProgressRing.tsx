import { useId } from 'react'
import { useCountUp } from '../hooks/useCountUp'

interface ProgressRingProps {
  completed: number
  total: number
}

export function ProgressRing({ completed, total }: ProgressRingProps) {
  const gradientId = useId()
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0
  const displayPercent = useCountUp(percent, 1000)

  const size = 160
  const stroke = 10
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (percent / 100) * circumference

  return (
    <div className="tml-progress-ring">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="tml-progress-ring__svg"
      >
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--tml-orange)" />
            <stop offset="100%" stopColor="var(--tml-orange-mid)" />
          </linearGradient>
        </defs>
        {/* 배경 트랙 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--tml-rule)"
          strokeWidth={stroke}
        />
        {/* 프로그레스 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="tml-progress-ring__circle"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="tml-progress-ring__label">
        <span className="tml-progress-ring__percent">{displayPercent}</span>
        <span className="tml-progress-ring__unit">%</span>
      </div>
    </div>
  )
}
