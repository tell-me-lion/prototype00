import { useState, useEffect, useRef } from 'react'

interface ProgressRingProps {
  completed: number
  total: number
}

function useCountUp(target: number, duration = 1000) {
  const [value, setValue] = useState(0)
  const rafRef = useRef(0)

  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = performance.now()
    const animate = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * target))
      if (progress < 1) rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return value
}

export function ProgressRing({ completed, total }: ProgressRingProps) {
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
          <linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--tml-orange)" />
            <stop offset="100%" stopColor="#FF9F4A" />
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
          stroke="url(#ring-gradient)"
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
