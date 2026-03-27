/* useProcessingStatus — 강의/주차 처리 상태를 2초 간격으로 폴링한다. */

import { useEffect, useRef, useState } from 'react'
import type { ProcessingStatusResponse } from '../types/models'
import { fetchLectureStatus, fetchWeekStatus } from '../services/api'

interface UseProcessingStatusOptions {
  lectureId?: string
  week?: number
  enabled: boolean
  interval?: number
  onComplete?: () => void
  onError?: (message: string) => void
}

interface UseProcessingStatusReturn {
  status: ProcessingStatusResponse | null
  isPolling: boolean
  error: string | null
}

export function useProcessingStatus({
  lectureId,
  week,
  enabled,
  interval = 2000,
  onComplete,
  onError,
}: UseProcessingStatusOptions): UseProcessingStatusReturn {
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // refs로 콜백을 감싸 stale closure 방지
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  })

  useEffect(() => {
    if (!enabled) return

    let stopped = false

    async function poll() {
      if (stopped) return
      try {
        const result = lectureId
          ? await fetchLectureStatus(lectureId)
          : await fetchWeekStatus(week!)
        if (stopped) return
        setStatus(result)

        if (result.status === 'completed') {
          onCompleteRef.current?.()
          return
        }
        if (result.status === 'error') {
          const msg = result.error_message ?? '처리 중 오류가 발생했습니다.'
          setError(msg)
          onErrorRef.current?.(msg)
          return
        }
      } catch {
        // 네트워크 오류 시 폴링 유지
      }
    }

    poll()
    const id = setInterval(poll, interval)
    return () => {
      stopped = true
      clearInterval(id)
    }
  }, [enabled, lectureId, week, interval])

  // isPolling: enabled이고 완료/오류 상태가 아닐 때
  const isPolling =
    enabled &&
    error === null &&
    (status === null ||
      (status.status !== 'completed' && status.status !== 'error'))

  return { status, isPolling, error }
}
