interface QuizTestCase {
  input?: string
  expected_output: string
}

export interface TestResult {
  input?: string
  expected: string
  actual: string
  passed: boolean
}

interface OutputPanelProps {
  stdout: string | null
  stderr: string | null
  testResults: TestResult[] | null
  error: string | null
}

export function runTestCases(
  stdout: string,
  testCases: QuizTestCase[],
): TestResult[] {
  const outputLines = stdout.trimEnd().split('\n')

  return testCases.map((tc, i) => {
    const actual = (outputLines[i] ?? '').trim()
    const expected = tc.expected_output.trim()
    return {
      input: tc.input,
      expected,
      actual,
      passed: actual === expected,
    }
  })
}

export function OutputPanel({ stdout, stderr, testResults, error }: OutputPanelProps) {
  if (error) {
    return (
      <div className="output-panel">
        <div className="output-panel__header">실행 결과</div>
        <pre className="output-panel__error">{error}</pre>
      </div>
    )
  }

  if (stdout === null && stderr === null && !testResults) return null

  const allPassed = testResults?.every((r) => r.passed) ?? false

  return (
    <div className="output-panel">
      <div className="output-panel__header">실행 결과</div>

      {stdout !== null && stdout.length > 0 && (
        <pre className="output-panel__stdout">{stdout}</pre>
      )}

      {stderr !== null && stderr.length > 0 && (
        <pre className="output-panel__error">{stderr}</pre>
      )}

      {testResults && testResults.length > 0 && (
        <div className="output-panel__tests">
          <div className="output-panel__tests-header">
            {allPassed ? '✓ 모든 테스트 통과!' : `✗ ${testResults.filter((r) => !r.passed).length}개 실패`}
          </div>
          <div className="output-panel__tests-list">
            {testResults.map((r, i) => (
              <div
                key={i}
                className={`output-panel__test ${r.passed ? 'output-panel__test--pass' : 'output-panel__test--fail'}`}
              >
                <span className="output-panel__test-icon">{r.passed ? '✓' : '✗'}</span>
                <div className="output-panel__test-detail">
                  {r.input && (
                    <span className="output-panel__test-label">
                      입력: <code>{r.input}</code>
                    </span>
                  )}
                  <span className="output-panel__test-label">
                    기대: <code>{r.expected}</code>
                  </span>
                  {!r.passed && (
                    <span className="output-panel__test-label output-panel__test-label--actual">
                      실제: <code>{r.actual}</code>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
