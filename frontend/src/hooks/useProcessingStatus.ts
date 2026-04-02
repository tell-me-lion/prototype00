/* useProcessingStatus — 강의/주차 처리 상태를 5초 간격으로 폴링한다. */

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
  onPartial?: () => void  // 재개 가능 상태 감지 시 호출
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
  interval = 5000,
  onComplete,
  onError,
  onPartial,
}: UseProcessingStatusOptions): UseProcessingStatusReturn {
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // refs로 콜백을 감싸 stale closure 방지
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)
  const onPartialRef = useRef(onPartial)
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
    onPartialRef.current = onPartial
  })

  useEffect(() => {
    if (!enabled) return
    if (!lectureId && week === undefined) {
      console.error('useProcessingStatus: lectureId 또는 week 중 하나를 제공해야 합니다')
      return
    }

    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    let networkRetryCount = 0     // DNS/네트워크 에러 전용 카운터
    let apiRetryCount = 0         // API 응답 에러 전용 카운터
    let emptyStepsCount = 0
    let lastLogTime = 0
    let lastRunningStep = ''      // 현재 running 단계 이름 추적
    let lastStatus = ''           // 이전 폴링의 status 추적
    const LOG_INTERVAL = 60000 // 콘솔 로그는 60초마다
    const MAX_NETWORK_RETRIES = 20  // 네트워크 에러는 넉넉하게
    const MAX_API_RETRIES = 5       // API 에러는 기존대로
    const BACKOFF_CAP_MS = 30000    // 백오프 상한 30초
    const MAX_EMPTY_STEPS = 10
    const MAX_POLL_MS = 60 * 60 * 1000 // 60분 타임아웃
    const pollStartTime = Date.now()

    async function poll() {
      if (stopped) return

      // BUG-2: 전체 폴링 타임아웃
      if (Date.now() - pollStartTime > MAX_POLL_MS) {
        const msg = '처리가 계속 진행 중일 수 있습니다. 페이지를 새로고침하면 결과를 확인할 수 있습니다.'
        console.error(`[폴링] 전체 타임아웃 초과 (${MAX_POLL_MS / 60000}분)`)
        setError(msg)
        onErrorRef.current?.(msg)
        return
      }

      const target = lectureId ? `lecture:${lectureId}` : `week:${week}`
      const now = Date.now()
      const timerFired = now - lastLogTime >= LOG_INTERVAL
      try {
        const result = lectureId
          ? await fetchLectureStatus(lectureId)
          : await fetchWeekStatus(week!)
        if (stopped) return

        networkRetryCount = 0
        apiRetryCount = 0
        setStatus(result)

        const steps = result.steps ?? []

        // 단계 변경 감지: running step 이름 또는 전체 status가 바뀌었을 때
        const currentRunningStep = steps.find((s) => s.status === 'running')?.name ?? ''
        const stepChanged = currentRunningStep !== lastRunningStep
        const statusChanged = result.status !== lastStatus
        lastRunningStep = currentRunningStep
        lastStatus = result.status

        // 로그 출력 조건: 1분 경과 OR 단계/상태 변경
        const shouldLog = timerFired || stepChanged || statusChanged
        if (shouldLog) {
          lastLogTime = now
          const doneCount = steps.filter((s) => s.status === 'done').length
          const isRunning = steps.some((s) => s.status === 'running')
          const percent = steps.length > 0
            ? doneCount * Math.floor(100 / steps.length) + (isRunning ? Math.floor(50 / steps.length) : 0)
            : null
          const percentLabel = percent !== null ? ` ${percent}% (${doneCount}/${steps.length})` : ''
          const runningDetail = currentRunningStep ? ` [${currentRunningStep}]` : ''
          console.log(`[폴링] ${target} — ${result.status}${percentLabel}${runningDetail}`)
        }

        if (result.status === 'completed') {
          console.log(`[폴링] ${target} — 완료!`)
          onCompleteRef.current?.()
          return
        }
        if (result.status === 'partial' || result.status === 'idle') {
          console.log(`[폴링] ${target} — 재개 가능 상태 감지`)
          onPartialRef.current?.()
          return
        }
        if (result.status === 'error') {
          const msg = result.error_message ?? '처리 중 오류가 발생했습니다.'
          console.error(`[폴링] ${target} — 에러:`, msg)
          setError(msg)
          onErrorRef.current?.(msg)
          return
        }

        // processing + steps 빈 배열 연속 감지
        if (result.status === 'processing' && steps.length === 0) {
          emptyStepsCount++
          if (emptyStepsCount >= MAX_EMPTY_STEPS) {
            const msg = '처리 상태를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.'
            console.error(`[폴링] ${target} — 빈 steps 연속 ${MAX_EMPTY_STEPS}회 초과`)
            setError(msg)
            onErrorRef.current?.(msg)
            return
          }
        } else {
          emptyStepsCount = 0
        }

        timer = setTimeout(poll, interval)
      } catch (err) {
        if (stopped) return

        // TASK-001: 네트워크 에러와 API 에러의 재시도 카운터 분리
        const isNetworkError = err instanceof TypeError
          || (err instanceof Error && /network|fetch|abort|dns|ENOTFOUND|ERR_NAME_NOT_RESOLVED/i.test(err.message))
        if (isNetworkError) {
          networkRetryCount++
          const delay = Math.min(interval * Math.pow(2, networkRetryCount), BACKOFF_CAP_MS)
          console.error(`[폴링] ${target} — 네트워크 에러 (${networkRetryCount}/${MAX_NETWORK_RETRIES}):`, err)
          if (networkRetryCount >= MAX_NETWORK_RETRIES) {
            const msg = '서버와 연결할 수 없습니다. 네트워크를 확인해주세요.'
            console.error(`[폴링] ${target} — 네트워크 재시도 초과, 에러로 전환`)
            setError(msg)
            onErrorRef.current?.(msg)
            return
          }
          timer = setTimeout(poll, delay)
        } else {
          apiRetryCount++
          const delay = Math.min(interval * Math.pow(2, apiRetryCount), BACKOFF_CAP_MS)
          console.error(`[폴링] ${target} — API 요청 실패 (${apiRetryCount}/${MAX_API_RETRIES}):`, err)
          if (apiRetryCount >= MAX_API_RETRIES) {
            const msg = '서버와 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'
            console.error(`[폴링] ${target} — API 재시도 초과, 에러로 전환`)
            setError(msg)
            onErrorRef.current?.(msg)
            return
          }
          timer = setTimeout(poll, delay)
        }
      }
    }

    poll()
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [enabled, lectureId, week, interval])

  // isPolling: enabled이고 완료/오류 상태가 아닐 때 (queued/processing 모두 폴링)
  const isPolling =
    enabled &&
    error === null &&
    (status === null ||
      (status.status !== 'completed' && status.status !== 'error' && status.status !== 'idle' && status.status !== 'partial'))

  return { status, isPolling, error }
}
