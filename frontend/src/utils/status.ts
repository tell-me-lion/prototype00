import type { ProcessingStatus } from '../types/models'

/**
 * 강의의 실제 처리 상태를 반환한다.
 * 로컬 processingSet에 있으면 'processing', 아니면 서버 상태 사용.
 */
export function getEffectiveLectureStatus(
  lectureId: string,
  serverStatus: ProcessingStatus,
  processingSet: Set<string>,
  erroredSet?: Set<string>,
): ProcessingStatus {
  if (processingSet.has(lectureId)) return 'processing'
  if (erroredSet?.has(lectureId)) return 'error'
  return serverStatus
}

/**
 * 주차의 실제 처리 상태를 반환한다.
 * - 로컬 processingSet에 있으면 'processing'
 * - 서버가 processing이면 'processing' (다른 세션에서 시작한 경우 포함)
 * - 그 외: 서버 상태
 */
export function getEffectiveWeekStatus(
  week: number,
  serverStatus: ProcessingStatus,
  processingSet: Set<number>,
): ProcessingStatus {
  if (processingSet.has(week)) return 'processing'
  if (serverStatus === 'processing') return 'processing'
  return serverStatus
}
