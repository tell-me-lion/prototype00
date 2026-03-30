import { lazy, Suspense, useEffect, useState } from 'react'

const MonacoEditor = lazy(() => import('@monaco-editor/react'))

interface CodeEditorProps {
  language: string
  starterCode: string
  onRun: (code: string) => void
  running: boolean
}

const LANG_MAP: Record<string, string> = {
  python: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  java: 'java',
  sql: 'sql',
  c: 'c',
  cpp: 'cpp',
  go: 'go',
  rust: 'rust',
}

function useTheme() {
  const [dark, setDark] = useState(
    () => document.documentElement.getAttribute('data-theme') === 'dark',
  )
  useEffect(() => {
    const obs = new MutationObserver(() => {
      setDark(document.documentElement.getAttribute('data-theme') === 'dark')
    })
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])
  return dark
}

export function CodeEditor({ language, starterCode, onRun, running }: CodeEditorProps) {
  const [code, setCode] = useState(starterCode)
  const dark = useTheme()

  const handleReset = () => setCode(starterCode)

  return (
    <div className="code-editor">
      <div className="code-editor__toolbar">
        <span className="code-editor__lang-badge">
          {language.toUpperCase()}
        </span>
        <div className="code-editor__actions">
          <button
            className="code-editor__btn code-editor__btn--reset"
            onClick={handleReset}
            disabled={running}
          >
            초기화
          </button>
          <button
            className="code-editor__btn code-editor__btn--run"
            onClick={() => onRun(code)}
            disabled={running}
          >
            {running ? (
              <span className="code-editor__spinner" />
            ) : (
              '▶'
            )}
            {running ? '실행 중…' : '실행'}
          </button>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="code-editor__loading">에디터 로딩 중…</div>
        }
      >
        <MonacoEditor
          height="220px"
          language={LANG_MAP[language] ?? 'plaintext'}
          theme={dark ? 'vs-dark' : 'light'}
          value={code}
          onChange={(v) => setCode(v ?? '')}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: 'var(--font-mono)',
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            padding: { top: 12, bottom: 12 },
          }}
        />
      </Suspense>
    </div>
  )
}
