import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100%', gap: 12,
          background: '#120d07', color: '#c04040', fontFamily: 'Georgia, serif',
        }}>
          <div style={{ fontSize: 32 }}>⚠</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>Something went wrong</div>
          <div style={{ fontSize: 12, color: '#9a7a50', maxWidth: 480, textAlign: 'center' }}>
            {this.state.error.message}
          </div>
          <button
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: 8, padding: '8px 20px', background: '#3d2913',
              border: '1px solid #7a5228', borderRadius: 6,
              color: '#e8b040', cursor: 'pointer', fontSize: 12,
            }}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
