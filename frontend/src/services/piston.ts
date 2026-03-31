const PISTON_URL = 'https://emkc.org/api/v2/piston/execute'
const TIMEOUT_MS = 10_000
const MAX_CODE_LENGTH = 10_000
const RATE_LIMIT_MS = 2_000

let lastExecutionTime = 0

export interface PistonRunResult {
  stdout: string
  stderr: string
  code: number
  signal: string | null
}

export interface PistonResponse {
  run: PistonRunResult
  compile?: PistonRunResult
}

const LANGUAGE_VERSIONS: Record<string, string> = {
  python: '3.10.0',
  javascript: '18.15.0',
  java: '15.0.2',
  sql: '*',
  typescript: '5.0.3',
  c: '10.2.0',
  cpp: '10.2.0',
  go: '1.16.2',
  rust: '1.68.2',
}

export async function executeCode(
  language: string,
  code: string,
  stdin?: string,
): Promise<PistonResponse> {
  if (code.length > MAX_CODE_LENGTH) {
    throw new Error(`코드가 너무 깁니다 (최대 ${MAX_CODE_LENGTH.toLocaleString()}자)`)
  }

  const now = Date.now()
  if (now - lastExecutionTime < RATE_LIMIT_MS) {
    throw new Error('너무 빠르게 실행하고 있습니다. 잠시 후 다시 시도해주세요.')
  }
  lastExecutionTime = now

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const res = await fetch(PISTON_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        language,
        version: LANGUAGE_VERSIONS[language] ?? '*',
        files: [{ content: code }],
        stdin: stdin ?? '',
      }),
    })

    if (!res.ok) {
      throw new Error(`Piston API error: ${res.status}`)
    }

    return (await res.json()) as PistonResponse
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('코드 실행 시간이 초과되었습니다 (10초)')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}
