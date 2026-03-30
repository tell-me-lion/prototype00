const PISTON_URL = 'https://emkc.org/api/v2/piston/execute'
const TIMEOUT_MS = 10_000

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
