/**
 * ErrorBoundary - catches React errors and prevents white screen crashes
 */

import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px',
          backgroundColor: '#f8f9fa'
        }}>
          <div style={{
            maxWidth: '600px',
            textAlign: 'center',
            padding: '40px',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '64px', marginBottom: '20px' }}>⚠️</div>
            <h2 style={{ color: '#dc3545', marginBottom: '16px' }}>
              Bir hata oluştu
            </h2>
            <p style={{ color: '#666', marginBottom: '24px' }}>
              Uygulama beklenmeyen bir hatayla karşılaştı.
            </p>
            {import.meta.env.VITE_DEBUG_UI && this.state.error && (
              <pre style={{
                textAlign: 'left',
                padding: '12px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
                fontSize: '12px',
                overflow: 'auto',
                maxHeight: '200px',
                color: '#dc3545'
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              style={{
                marginTop: '20px',
                padding: '12px 24px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Sayfayı Yenile
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
