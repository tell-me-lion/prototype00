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
  interval = 30000,
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
    if (!lectureId && week === undefined) {
      console.error('useProcessingStatus: lectureId 또는 week 중 하나를 제공해야 합니다')
      return
    }

    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    let retryCount = 0
    const MAX_RETRIES = 5

    async function poll() {
      if (stopped) return
      const target = lectureId ? `lecture:${lectureId}` : `week:${week}`
      console.log(`[폴링] ${target} — 상태 조회 중... (재시도: ${retryCount})`)
      try {
        const result = lectureId
          ? await fetchLectureStatus(lectureId)
          : await fetchWeekStatus(week!)
        if (stopped) return

        retryCount = 0
        setStatus(result)
        console.log(`[폴링] ${target} — 응답:`, result.status, result.steps ?? '', result.error_message ?? '')

        if (result.status === 'completed') {
          console.log(`[폴링] ${target} — 완료!`)
          onCompleteRef.current?.()
          return
        }
        if (result.status === 'error') {
          const msg = result.error_message ?? '처리 중 오류가 발생했습니다.'
          console.error(`[폴링] ${target} — 백엔드 에러:`, msg)
          setError(msg)
          onErrorRef.current?.(msg)
          return
        }

        timer = setTimeout(poll, interval)
      } catch (err) {
        if (stopped) return
        retryCount++
        console.error(`[폴링] ${target} — 네트워크/요청 실패 (${retryCount}/${MAX_RETRIES}):`, err)
        if (retryCount >= MAX_RETRIES) {
          const msg = '서버와 연결할 수 없습니다. 네트워크를 확인해주세요.'
          console.error(`[폴링] ${target} — 최대 재시도 초과, 에러로 전환`)
          setError(msg)
          onErrorRef.current?.(msg)
          return
        }
        timer = setTimeout(poll, interval * Math.pow(2, retryCount))
      }
    }

    poll()
    return () => {
      stopped = true
      clearTimeout(timer)
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
