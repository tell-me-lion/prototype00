import { useState, useCallback, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import type { WeekSummary, Lecture, ProcessingStatus } from '../types/models'
import { triggerLectureProcess, triggerWeekProcess } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProcessingStatus as ProcessingStatusUI } from '../components/ProcessingStatus'
import { getEffectiveLectureStatus, getEffectiveWeekStatus } from '../utils/status'
import { useWeeks } from '../hooks/useWeeks'

// ── 썸네일 그래디언트 헬퍼 ──

function getLectureThumbnailGradient(date: string, week: number): string {
  const hues = [210, 25, 170, 340]
  const baseHue = hues[(week - 1) % hues.length]
  const dayOffset = new Date(date).getDay() * 8
  return `linear-gradient(135deg, hsl(${baseHue + dayOffset}, 60%, 35%), hsl(${baseHue + dayOffset + 30}, 50%, 25%))`
}

// ── WeekFilter ──

interface WeekFilterProps {
  weeks: number[]
  activeWeek: number | null
  onSelect: (week: number | null) => void
}

function WeekFilter({ weeks, activeWeek, onSelect }: WeekFilterProps) {
  return (
    <div className="tml-week-tabs tml-animate" role="tablist" aria-label="주차 필터" style={{ marginTop: 8 }}>
      <button
        role="tab"
        aria-selected={activeWeek === null}
        className={`tml-week-tab${activeWeek === null ? ' tml-week-tab--active' : ''}`}
        onClick={() => onSelect(null)}
      >
        전체
      </button>
      {weeks.map((week) => (
        <button
          key={week}
          role="tab"
          aria-selected={activeWeek === week}
          className={`tml-week-tab${activeWeek === week ? ' tml-week-tab--active' : ''}`}
          onClick={() => onSelect(week)}
        >
          {week}주차
        </button>
      ))}
    </div>
  )
}

// ── LectureCard ──

interface LectureCardProps {
  lecture: Lecture
  isSelected: boolean
  onToggleSelect: (lectureId: string) => void
  onViewResults: (lectureId: string) => void
  onProcessComplete: (lectureId: string) => void
  onProcessError: (lectureId: string) => void
  onRetry: (lectureId: string) => void
  onResume: (lectureId: string) => void
}

function LectureCard({ lecture, isSelected, onToggleSelect, onViewResults, onProcessComplete, onProcessError, onRetry, onResume }: LectureCardProps) {
  const { lecture_id, date, day_of_week, week, course_name, status, result_summary } = lecture
  const gradient = getLectureThumbnailGradient(date, week)

  const handleCardClick = () => {
    if (status === 'idle') onToggleSelect(lecture_id)
    else if (status === 'completed') onViewResults(lecture_id)
  }

  const isClickable = status === 'idle' || status === 'completed'

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      handleCardClick()
    }
  }

  return (
    <div
      className={[
        'tml-lecture-card tml-card',
        isClickable ? 'tml-lecture-card--selectable' : '',
        isSelected ? 'tml-lecture-card--selected' : '',
      ].join(' ').trim()}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={isClickable ? handleCardClick : undefined}
      onKeyDown={isClickable ? handleKeyDown : undefined}
    >
      <div className="tml-lecture-card__thumb" style={{ background: gradient, position: 'relative' }}>
        <span className="tml-lecture-card__date-badge">
          {date.slice(5)} ({day_of_week})
        </span>
        {status === 'idle' && (
          <span className={`tml-lecture-card__checkbox${isSelected ? ' tml-lecture-card__checkbox--checked' : ''}`}>
            {isSelected && (
              <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </span>
        )}
      </div>

      <div className="tml-lecture-card__body">
        <p className="tml-lecture-card__course">{course_name}</p>
        <p className="tml-lecture-card__week-label">Week {week}</p>

        <hr className="tml-lecture-card__rule" />

        {status === 'queued' && (
          <div className="tml-lecture-card__footer">
            <div className="tml-lecture-card__queued">
              <span className="tml-lecture-card__queued-icon">⏳</span>
              <span className="tml-lecture-card__queued-msg">대기 중</span>
            </div>
          </div>
        )}

        {status === 'processing' && (
          <div className="tml-lecture-card__footer">
            <ProcessingStatusUI
              lectureId={lecture_id}
              onComplete={() => onProcessComplete(lecture_id)}
              onError={() => onProcessError(lecture_id)}
              onResume={() => onResume(lecture_id)}
            />
          </div>
        )}

        {status === 'partial' && (
          <div className="tml-lecture-card__footer">
            <div className="tml-lecture-card__resume">
              <span className="tml-lecture-card__resume-msg">이전 작업 이어서 진행 가능</span>
              <button
                className="tml-lecture-card__resume-btn"
                onClick={(e) => { e.stopPropagation(); onResume(lecture_id) }}
              >
                재개하기 →
              </button>
            </div>
          </div>
        )}

        {status === 'completed' && result_summary && (
          <div className="tml-lecture-card__footer">
            <div className="tml-lecture-card__summary">
              <span>개념 {result_summary.concept_count}개</span>
              <span>퀴즈 {result_summary.quiz_count}개</span>
            </div>
            <span className="tml-lecture-card__result-btn">결과 보기 →</span>
          </div>
        )}

        {status === 'error' && (
          <div className="tml-lecture-card__footer">
            <p className="tml-lecture-card__error">오류가 발생했습니다</p>
            <button
              className="btn-primary"
              style={{
                fontSize: '0.8125rem',
                padding: '6px 14px',
                width: '100%',
                background: 'var(--tml-wrong)',
              }}
              onClick={(e) => { e.stopPropagation(); onRetry(lecture_id) }}
            >
              재시도
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── LectureCardSkeleton ──

function LectureCardSkeleton() {
  return (
    <div className="tml-lecture-card tml-card">
      <div
        className="tml-skeleton"
        style={{ height: 80, borderRadius: '5px 5px 0 0', flexShrink: 0 }}
      />
      <div className="tml-lecture-card__body">
        <div className="tml-skeleton" style={{ height: 13, width: '72%', borderRadius: 4, marginBottom: 8 }} />
        <div className="tml-skeleton" style={{ height: 11, width: '40%', borderRadius: 4, marginBottom: 12 }} />
        <div className="tml-skeleton" style={{ height: 32, borderRadius: 5 }} />
      </div>
    </div>
  )
}

// ── WeekGuideCard ──

interface WeekGuideCardProps {
  week: number
  lectureCount: number
  completedCount: number
  status: ProcessingStatus
  onProcess: (week: number) => void
  onViewResults: (week: number) => void
  onProcessComplete: (week: number) => void
  onProcessError: (week: number) => void
  onAnalyzeAll: () => void
}

function WeekGuideCard({ week, lectureCount, completedCount, status, onProcess, onViewResults, onProcessComplete, onProcessError, onAnalyzeAll }: WeekGuideCardProps) {
  const [showConfirm, setShowConfirm] = useState(false)
  const allCompleted = completedCount >= lectureCount && lectureCount > 0
  const remaining = lectureCount - completedCount

  const handleGuideClick = () => {
    if (allCompleted) {
      onProcess(week)
    } else {
      setShowConfirm(true)
    }
  }

  const handleAnalyzeAll = () => {
    setShowConfirm(false)
    onAnalyzeAll()
  }

  return (
    <div className="tml-week-guide-card tml-card">
      <div className="tml-week-guide-card__bar" />
      {showConfirm ? (
        <div className="tml-week-guide-card__confirm">
          <p className="tml-week-guide-card__confirm-msg">
            {remaining}개 강의 분석이 남아있어요.
            <br />
            먼저 이 주차 강의를 모두 분석할까요?
          </p>
          <div className="tml-week-guide-card__confirm-actions">
            <button className="btn-primary" style={{ fontSize: '0.8125rem', padding: '6px 14px' }} onClick={handleAnalyzeAll}>
              지금 분석하기
            </button>
            <button className="tml-week-guide-card__cancel-btn" onClick={() => setShowConfirm(false)}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <div className="tml-week-guide-card__content">
          <div>
            <p className="tml-week-guide-card__title">
              {week}주차 전체 학습 가이드
            </p>
            <p className="tml-week-guide-card__desc">
              {lectureCount}개 강의 통합 분석
            </p>
          </div>

          <div style={{ flexShrink: 0 }}>
            {status === 'completed' ? (
              <button
                className="tml-lecture-card__result-btn"
                onClick={() => onViewResults(week)}
              >
                가이드 보기 →
              </button>
            ) : status === 'processing' ? (
              <ProcessingStatusUI
                week={week}
                onComplete={() => onProcessComplete(week)}
                onError={() => onProcessError(week)}
              />
            ) : (
              <button
                className="btn-primary"
                style={{ fontSize: '0.8125rem', padding: '6px 14px' }}
                onClick={handleGuideClick}
              >
                가이드 생성 →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── WeekSection ──

interface WeekSectionProps {
  weekSummary: WeekSummary
  processingLectures: Set<string>
  erroredLectures: Set<string>
  processingWeeks: Set<number>
  selectedIds: Set<string>
  onToggleSelect: (lectureId: string) => void
  onViewResults: (lectureId: string) => void
  onProcessComplete: (lectureId: string) => void
  onProcessError: (lectureId: string) => void
  onRetry: (lectureId: string) => void
  onResume: (lectureId: string) => void
  onProcessWeek: (week: number) => void
  onViewWeekResults: (week: number) => void
  onWeekProcessComplete: (week: number) => void
  onWeekProcessError: (week: number) => void
}

function WeekSection({
  weekSummary,
  processingLectures,
  erroredLectures,
  processingWeeks,
  selectedIds,
  onToggleSelect,
  onViewResults,
  onProcessComplete,
  onProcessError,
  onRetry,
  onResume,
  onProcessWeek,
  onViewWeekResults,
  onWeekProcessComplete,
  onWeekProcessError,
}: WeekSectionProps) {
  const { week, lecture_count, completed_count, date_range, lectures } = weekSummary

  const effectiveWeekStatus = getEffectiveWeekStatus(week, weekSummary.status, processingWeeks)

  const handleAnalyzeAll = () => {
    lectures.forEach((lecture) => {
      const effectiveStatus = getEffectiveLectureStatus(lecture.lecture_id, lecture.status, processingLectures, erroredLectures)
      if (effectiveStatus !== 'completed' && effectiveStatus !== 'processing') {
        onRetry(lecture.lecture_id)
      }
    })
  }

  return (
    <section className="tml-week-section tml-animate">
      <div className="tml-week-section__header">
        <div className="tml-week-section__title-row">
          <h2 className="tml-week-section__title">{week}주차</h2>
          <span className="tml-week-section__range">{date_range}</span>
        </div>
        <span className="tml-week-section__progress">
          {lecture_count}강의 · {completed_count}완료
        </span>
      </div>

      <div className="tml-lecture-grid">
        {lectures.map((lecture) => {
          const effectiveStatus = getEffectiveLectureStatus(lecture.lecture_id, lecture.status, processingLectures, erroredLectures)
          return (
            <LectureCard
              key={lecture.lecture_id}
              lecture={{ ...lecture, status: effectiveStatus }}
              isSelected={selectedIds.has(lecture.lecture_id)}
              onToggleSelect={onToggleSelect}
              onViewResults={onViewResults}
              onProcessComplete={onProcessComplete}
              onProcessError={onProcessError}
              onRetry={onRetry}
              onResume={onResume}
            />
          )
        })}
      </div>

      <WeekGuideCard
        week={week}
        lectureCount={lecture_count}
        completedCount={completed_count}
        status={effectiveWeekStatus}
        onProcess={onProcessWeek}
        onViewResults={onViewWeekResults}
        onProcessComplete={onWeekProcessComplete}
        onProcessError={onWeekProcessError}
        onAnalyzeAll={handleAnalyzeAll}
      />
    </section>
  )
}

// ── RightPanel ──

interface RightPanelProps {
  weeks: WeekSummary[]
  selectedIds: Set<string>
  processingWeeks: Set<number>
  onDeselect: (lectureId: string) => void
  onStartSelected: () => void
  onViewResults: (lectureId: string) => void
  onViewWeekResults: (week: number) => void
  onProcessWeek: (week: number) => void
}

function RightPanel({
  weeks,
  selectedIds,
  processingWeeks,
  onDeselect,
  onStartSelected,
  onViewResults,
  onViewWeekResults,
  onProcessWeek,
}: RightPanelProps) {
  // 모든 강의 플랫 리스트
  const allLectures = weeks.flatMap((w) => w.lectures)

  // 선택된 강의 (idle)
  const selectedLectures = allLectures.filter((l) => selectedIds.has(l.lecture_id))

  // 분석 완료된 강의
  const completedLectures = allLectures.filter((l) => l.status === 'completed')

  return (
    <aside className="tml-right-panel">
      {/* 분석 대기 */}
      <div className={`tml-right-panel__section tml-right-panel__section--queue${selectedIds.size > 0 ? ' tml-right-panel__section--has-items' : ''}`}>
        <p className="tml-right-panel__section-title" style={{ color: 'var(--tml-orange)' }}>
          분석 대기 ({selectedIds.size}개)
        </p>
        {selectedLectures.length === 0 ? (
          <div className="tml-right-panel__hint">
            <p className="tml-right-panel__hint-text">왼쪽 강의를 클릭해서 선택하세요</p>
          </div>
        ) : (
          <ul className="tml-right-panel__list">
            {selectedLectures.map((l) => (
              <li key={l.lecture_id} className="tml-right-panel__item">
                <span className="tml-right-panel__item-label">
                  {l.date.slice(5)} ({l.day_of_week})
                </span>
                <button
                  className="tml-right-panel__remove"
                  onClick={() => onDeselect(l.lecture_id)}
                  aria-label="선택 해제"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          className="btn-primary"
          style={{
            width: '100%',
            marginTop: 12,
            fontSize: '0.8125rem',
            padding: '10px 14px',
            opacity: selectedIds.size === 0 ? 0.4 : 1,
            cursor: selectedIds.size === 0 ? 'not-allowed' : 'pointer',
          }}
          disabled={selectedIds.size === 0}
          onClick={onStartSelected}
        >
          분석 시작 →
        </button>
      </div>

      {/* 분석 완료 */}
      <div className="tml-right-panel__section">
        <p className="tml-right-panel__section-title">
          분석 완료 ({completedLectures.length}개)
        </p>
        {completedLectures.length === 0 ? (
          <p className="tml-right-panel__empty">완료된 강의 없음</p>
        ) : (
          <ul className="tml-right-panel__list">
            {completedLectures.map((l) => (
              <li key={l.lecture_id} className="tml-right-panel__item">
                <span className="tml-right-panel__item-label">
                  {l.date.slice(5)} ({l.day_of_week})
                </span>
                <button
                  className="tml-lecture-card__result-btn"
                  style={{ fontSize: '0.75rem' }}
                  onClick={() => onViewResults(l.lecture_id)}
                >
                  결과보기→
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 학습 가이드 */}
      <div className="tml-right-panel__section">
        <p className="tml-right-panel__section-title">학습 가이드</p>
        {weeks.length === 0 ? (
          <p className="tml-right-panel__empty">데이터 없음</p>
        ) : (
          <ul className="tml-right-panel__list">
            {weeks.map((w) => {
              const effectiveStatus = getEffectiveWeekStatus(w.week, w.status, processingWeeks)
              return (
                <li key={w.week} className="tml-right-panel__item">
                  <span className="tml-right-panel__item-label">{w.week}주차</span>
                  {effectiveStatus === 'completed' ? (
                    <button
                      className="tml-lecture-card__result-btn"
                      style={{ fontSize: '0.75rem' }}
                      onClick={() => onViewWeekResults(w.week)}
                    >
                      완료 →
                    </button>
                  ) : effectiveStatus === 'processing' ? (
                    <span style={{ fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>분석 중…</span>
                  ) : (
                    <button
                      className="tml-right-panel__guide-btn"
                      onClick={() => onProcessWeek(w.week)}
                    >
                      생성 →
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </aside>
  )
}

// ── LecturesPage (메인 export) ──

export function LecturesPage() {
  const { weeks, loading, error } = useWeeks('강의 목록을 불러오지 못했습니다.')
  const [processingLectures, setProcessingLectures] = useState<Set<string>>(new Set())
  const [erroredLectures, setErroredLectures] = useState<Set<string>>(new Set())
  const [processingWeeks, setProcessingWeeks] = useState<Set<number>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [failedLectures, setFailedLectures] = useState<Set<string>>(new Set())
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // 서버 상태와 로컬 processingSet 동기화 (새로고침/뒤로가기 대응)
  useEffect(() => {
    const allLectures = weeks.flatMap((w) => w.lectures)
    // processing + partial 모두 폴링 대상 (partial은 폴링 후 재개 UI로 전환)
    const serverActiveIds = new Set(
      allLectures.filter((l) => l.status === 'processing' || l.status === 'partial').map((l) => l.lecture_id),
    )
    const serverCompletedIds = new Set(
      allLectures.filter((l) => l.status === 'completed').map((l) => l.lecture_id),
    )

    setProcessingLectures((prev) => {
      const next = new Set(prev)
      serverActiveIds.forEach((id) => next.add(id))
      serverCompletedIds.forEach((id) => next.delete(id))
      return next
    })
  }, [weeks])

  const activeWeek = searchParams.get('week') ? Number(searchParams.get('week')) : null

  const handleWeekSelect = useCallback(
    (week: number | null) => {
      if (week === null) setSearchParams({})
      else setSearchParams({ week: String(week) })
    },
    [setSearchParams],
  )

  const handleToggleSelect = useCallback((lectureId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(lectureId)) next.delete(lectureId)
      else next.add(lectureId)
      return next
    })
  }, [])

  const handleDeselect = useCallback((lectureId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.delete(lectureId)
      return next
    })
  }, [])

  const handleStartSelected = useCallback(async () => {
    const ids = [...selectedIds]
    setSelectedIds(new Set())
    setFailedLectures(new Set())
    const failed: string[] = []
    // 순차 요청: 백엔드 Semaphore(1)와 맞춰 하나씩 트리거
    for (const id of ids) {
      setProcessingLectures((prev) => new Set(prev).add(id))
      try {
        await triggerLectureProcess(id, false)
      } catch (err: unknown) {
        const status = (err as { status?: number }).status
        if (status === 409) {
          // 이미 처리 중/대기 중 → 폴링이 이어받으므로 spinner 유지
          continue
        }
        failed.push(id)
        setProcessingLectures((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
      }
    }
    if (failed.length > 0) {
      setFailedLectures(new Set(failed))
    }
  }, [selectedIds])

  const handleRetry = useCallback(async (lectureId: string) => {
    setErroredLectures((prev) => {
      const next = new Set(prev)
      next.delete(lectureId)
      return next
    })
    setProcessingLectures((prev) => new Set(prev).add(lectureId))
    try {
      await triggerLectureProcess(lectureId)
    } catch (err: unknown) {
      const status = (err as { status?: number }).status
      if (status === 409) {
        // 이미 처리 중/대기 중 → 폴링이 이어받으므로 spinner 유지
        return
      }
      setProcessingLectures((prev) => {
        const next = new Set(prev)
        next.delete(lectureId)
        return next
      })
    }
  }, [])

  const handleResume = useCallback(async (lectureId: string) => {
    setProcessingLectures((prev) => new Set(prev).add(lectureId))
    try {
      await triggerLectureProcess(lectureId, false)
    } catch (err: unknown) {
      const status = (err as { status?: number }).status
      if (status === 409) {
        // 이미 처리 중 → 폴링이 이어받으므로 spinner 유지
        return
      }
      // 그 외 에러 → spinner 해제
      setProcessingLectures((prev) => {
        const next = new Set(prev)
        next.delete(lectureId)
        return next
      })
    }
  }, [])

  const handleProcessComplete = useCallback(
    (lectureId: string) => {
      setProcessingLectures((prev) => {
        const next = new Set(prev)
        next.delete(lectureId)
        return next
      })
      // navigate(`/lecture/${lectureId}`) 삭제: 사용자가 직접 "결과 보기" 버튼을 누르도록 함
    },
    [],
  )

  const handleProcessError = useCallback((lectureId: string) => {
    setProcessingLectures((prev) => {
      const next = new Set(prev)
      next.delete(lectureId)
      return next
    })
    setErroredLectures((prev) => new Set(prev).add(lectureId))
  }, [])

  const handleProcessWeek = useCallback(async (week: number) => {
    setProcessingWeeks((prev) => new Set(prev).add(week))
    try {
      await triggerWeekProcess(week)
    } catch {
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
    }
  }, [])

  const handleWeekProcessComplete = useCallback(
    (week: number) => {
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
      // navigate(`/weekly/${week}`) 삭제 (명시적 액션 권장)
    },
    [],
  )

  const handleWeekProcessError = useCallback((week: number) => {
    setProcessingWeeks((prev) => {
      const next = new Set(prev)
      next.delete(week)
      return next
    })
  }, [])

  const weekNumbers = weeks.map((w) => w.week)
  const filteredWeeks =
    activeWeek !== null ? weeks.filter((w) => w.week === activeWeek) : weeks

  return (
    <main className="tml-page-container tml-page-container--hero">

      {/* 페이지 헤더 */}
      <div className="tml-animate">
        <p className="tml-page-eyebrow">Lecture List</p>
        <h1 className="tml-page-title">강의 목록</h1>
      </div>

      {/* 로딩 상태 */}
      {loading && (
        <div className="tml-lecture-grid">
          {[...Array(5)].map((_, i) => (
            <LectureCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* 에러 상태 */}
      {!loading && error && (
        <ErrorCard message={error} title="강의 목록 로드 실패" />
      )}

      {/* 처리 실패 알림 */}
      {failedLectures.size > 0 && (
        <div
          role="alert"
          style={{
            padding: '12px 16px',
            marginBottom: 16,
            borderRadius: 8,
            background: 'var(--tml-wrong-bg)',
            color: 'var(--tml-ink)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span>{failedLectures.size}개 강의 처리 시작에 실패했습니다.</span>
          <button
            onClick={() => setFailedLectures(new Set())}
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--tml-ink-muted)',
              fontSize: '1rem',
              padding: '0 4px',
            }}
            aria-label="닫기"
          >
            ×
          </button>
        </div>
      )}

      {/* 분할 패널 레이아웃 */}
      {!loading && !error && (
        <>
          {weeks.length === 0 ? (
            <div className="tml-empty" style={{ padding: '48px 24px', textAlign: 'center' }}>
              <p style={{ fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)', margin: 0 }}>
                등록된 강의가 없습니다.
              </p>
            </div>
          ) : (
            <>
              <WeekFilter weeks={weekNumbers} activeWeek={activeWeek} onSelect={handleWeekSelect} />

              <div className="tml-split-layout">
                {/* 왼쪽: 강의 목록 */}
                <div key={activeWeek} className="tml-week-content" style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
                  {filteredWeeks.map((weekSummary) => (
                    <WeekSection
                      key={weekSummary.week}
                      weekSummary={weekSummary}
                      processingLectures={processingLectures}
                      erroredLectures={erroredLectures}
                      processingWeeks={processingWeeks}
                      selectedIds={selectedIds}
                      onToggleSelect={handleToggleSelect}
                      onViewResults={(id) => navigate(`/lecture/${id}`)}
                      onProcessComplete={handleProcessComplete}
                      onProcessError={handleProcessError}
                      onRetry={handleRetry}
                      onResume={handleResume}
                      onProcessWeek={handleProcessWeek}
                      onViewWeekResults={(w) => navigate(`/weekly/${w}`)}
                      onWeekProcessComplete={handleWeekProcessComplete}
                      onWeekProcessError={handleWeekProcessError}
                    />
                  ))}
                </div>

                {/* 오른쪽: 분석 현황 패널 */}
                <RightPanel
                  weeks={weeks}
                  selectedIds={selectedIds}
                  processingWeeks={processingWeeks}
                  onDeselect={handleDeselect}
                  onStartSelected={handleStartSelected}
                  onViewResults={(id) => navigate(`/lecture/${id}`)}
                  onViewWeekResults={(w) => navigate(`/weekly/${w}`)}
                  onProcessWeek={handleProcessWeek}
                />
              </div>
            </>
          )}
        </>
      )}
    </main>
  )
}
