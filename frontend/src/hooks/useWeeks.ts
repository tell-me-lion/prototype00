import { useState, useEffect } from 'react'
import type { WeekSummary } from '../types/models'
import { fetchWeeks, ApiError } from '../services/api'

interface UseWeeksResult {
  weeks: WeekSummary[]
  loading: boolean
  error: string | null
  setWeeks: React.Dispatch<React.SetStateAction<WeekSummary[]>>
}

export function useWeeks(fallbackErrorMessage = '데이터를 불러오지 못했습니다.'): UseWeeksResult {
  const [weeks, setWeeks] = useState<WeekSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWeeks()
      .then(setWeeks)
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : fallbackErrorMessage)
      })
      .finally(() => setLoading(false))
  }, [fallbackErrorMessage])

  return { weeks, loading, error, setWeeks }
}
