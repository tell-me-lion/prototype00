import type { ProcessingStatus } from '../types/models'

/**
 * 강의의 실제 처리 상태를 반환한다.
 * 로컬 processingSet에 있으면 'processing', 아니면 서버 상태 사용.
 */
export function getEffectiveLectureStatus(
  lectureId: string,
  serverStatus: ProcessingStatus,
  processingSet: Set<string>,
): ProcessingStatus {
  return processingSet.has(lectureId) ? 'processing' : serverStatus
}

/**
 * 주차의 실제 처리 상태를 반환한다.
 * - 로컬 processingSet에 있으면 'processing'
 * - 서버가 processing인데 로컬에 없으면 'idle' (이전 세션 잔여)
 * - 그 외: 서버 상태
 */
export function getEffectiveWeekStatus(
  week: number,
  serverStatus: ProcessingStatus,
  processingSet: Set<number>,
): ProcessingStatus {
  if (processingSet.has(week)) return 'processing'
  if (serverStatus === 'processing' && !processingSet.has(week)) return 'idle'
  return serverStatus
}
