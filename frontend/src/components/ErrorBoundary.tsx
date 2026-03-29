import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="tml-not-found">
          <h1>문제가 발생했습니다</h1>
          <p className="tml-ink-secondary">{this.state.error.message}</p>
          <button
            className="btn-primary"
            onClick={() => {
              this.setState({ error: null })
              window.location.href = '/'
            }}
          >
            대시보드로 돌아가기
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
