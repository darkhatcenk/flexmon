import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { safeArray } from '../lib/safe'

export default function Alarms() {
  const [tenant, setTenant] = useState('')
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('')
  const [timeRange, setTimeRange] = useState('24h')
  const [page, setPage] = useState(0)
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const [aiExplanation, setAiExplanation] = useState<string>('')
  const [loadingAi, setLoadingAi] = useState(false)
  const pageSize = 50
  const queryClient = useQueryClient()

  // Fetch unified internal + external alerts
  const { data: alerts, isLoading, refetch } = useQuery({
    queryKey: ['alarms', tenant, severity, status, timeRange, page],
    queryFn: () => api.get('/v1/alarms', {
      params: {
        tenant_id: tenant || undefined,
        severity: severity || undefined,
        status: status || undefined,
        from: `now-${timeRange}`,
        to: 'now',
        page,
        size: pageSize
      }
    }),
    refetchInterval: 30000
  })

  // Acknowledge alarm mutation
  const acknowledgeMutation = useMutation({
    mutationFn: (alarmId: number) => api.patch(`/v1/alarms/${alarmId}/acknowledge`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      alert('Alarm acknowledged successfully')
    },
    onError: (error: any) => {
      alert(`Failed to acknowledge alarm: ${error.response?.data?.detail || error.message}`)
    }
  })

  // Resolve alarm mutation
  const resolveMutation = useMutation({
    mutationFn: (alarmId: number) => api.patch(`/v1/alarms/${alarmId}/resolve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alarms'] })
      alert('Alarm resolved successfully')
    },
    onError: (error: any) => {
      alert(`Failed to resolve alarm: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleSearch = () => {
    setPage(0)
    refetch()
  }

  const handleAiExplain = async (alarmId: number) => {
    setLoadingAi(true)
    setAiModalOpen(true)
    setAiExplanation('Analyzing alarm with AI...')

    try {
      const response = await api.get(`/v1/ai/explain/alert/${alarmId}`)
      setAiExplanation(response.data.explanation || 'No explanation available')
    } catch (error: any) {
      setAiExplanation(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setLoadingAi(false)
    }
  }

  const severityColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'critical':
        return '#dc3545'
      case 'error':
        return '#ff6b6b'
      case 'warning':
        return '#ffc107'
      case 'info':
        return '#17a2b8'
      default:
        return '#6c757d'
    }
  }

  const statusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return '#dc3545'
      case 'acknowledged':
        return '#ffc107'
      case 'resolved':
        return '#28a745'
      default:
        return '#6c757d'
    }
  }

  return (
    <div>
      <h2>Alarms & Alerts</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Unified view of internal (threshold) and external (webhook/forwarded) alerts
      </p>

      {/* Search and Filters */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>Filters</h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
          {/* Tenant Filter */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Tenant ID
            </label>
            <input
              type="text"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              placeholder="Filter by tenant"
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            />
          </div>

          {/* Severity Filter */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Severity
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            >
              <option value="">All</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          {/* Time Range */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Time Range
            </label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            >
              <option value="1h">Last hour</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleSearch}
          style={{
            marginTop: '15px',
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Search
        </button>
      </div>

      {/* Alarms Table */}
      <div className="card">
        <h3>
          Alarms ({safeArray(alerts?.data).length})
          {isLoading && <span style={{ marginLeft: '10px', color: '#999' }}>Loading...</span>}
        </h3>

        <div style={{ overflowX: 'auto', marginTop: '15px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Time</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Severity</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Host</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Tenant</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Type</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Message</th>
                <th style={{ padding: '10px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {safeArray(alerts?.data).map((alarm: any) => (
                <tr key={alarm.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px', whiteSpace: 'nowrap' }}>
                    {new Date(alarm.triggered_at || alarm.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: severityColor(alarm.severity),
                      color: 'white',
                      fontSize: '11px',
                      fontWeight: 'bold'
                    }}>
                      {alarm.severity?.toUpperCase() || 'INFO'}
                    </span>
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: statusColor(alarm.status),
                      color: 'white',
                      fontSize: '11px'
                    }}>
                      {alarm.status || 'active'}
                    </span>
                  </td>
                  <td style={{ padding: '10px', fontFamily: 'monospace' }}>
                    {alarm.host || '-'}
                  </td>
                  <td style={{ padding: '10px', color: '#666' }}>
                    {alarm.tenant_id || '-'}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: '3px',
                      backgroundColor: alarm.source === 'internal' ? '#17a2b8' : '#6c757d',
                      color: 'white',
                      fontSize: '10px'
                    }}>
                      {alarm.source || alarm.type || 'internal'}
                    </span>
                  </td>
                  <td style={{ padding: '10px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {alarm.message || alarm.description}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                    {alarm.status !== 'resolved' && (
                      <>
                        {alarm.status !== 'acknowledged' && (
                          <button
                            onClick={() => acknowledgeMutation.mutate(alarm.id)}
                            style={{
                              padding: '4px 8px',
                              marginRight: '5px',
                              backgroundColor: '#ffc107',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer',
                              fontSize: '11px'
                            }}
                          >
                            ACK
                          </button>
                        )}
                        <button
                          onClick={() => resolveMutation.mutate(alarm.id)}
                          style={{
                            padding: '4px 8px',
                            marginRight: '5px',
                            backgroundColor: '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '3px',
                            cursor: 'pointer',
                            fontSize: '11px'
                          }}
                        >
                          Resolve
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handleAiExplain(alarm.id)}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: 'pointer',
                        fontSize: '11px',
                        fontWeight: 'bold'
                      }}
                      title="Get AI explanation for this alarm"
                    >
                      🤖 AI
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(!alerts?.data || alerts.data.length === 0) && !isLoading && (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
              No alarms found matching your filters
            </div>
          )}
        </div>

        {/* Pagination */}
        {alerts?.data && alerts.data.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginTop: '20px' }}>
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              style={{
                padding: '8px 16px',
                backgroundColor: page === 0 ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: page === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              Previous
            </button>
            <span>Page {page + 1}</span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={alerts.data.length < pageSize}
              style={{
                padding: '8px 16px',
                backgroundColor: alerts.data.length < pageSize ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: alerts.data.length < pageSize ? 'not-allowed' : 'pointer'
              }}
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* AI Explanation Modal */}
      {aiModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{
            width: '700px',
            maxWidth: '90%',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h3 style={{ margin: 0 }}>🤖 AI Alarm Explanation</h3>
              <button
                onClick={() => setAiModalOpen(false)}
                style={{
                  padding: '5px 10px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
            </div>

            <div style={{
              padding: '15px',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '13px',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              minHeight: '200px'
            }}>
              {loadingAi ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  <div>Analyzing alarm with AI...</div>
                  <div style={{ marginTop: '10px', fontSize: '11px' }}>
                    This may take a few seconds
                  </div>
                </div>
              ) : (
                aiExplanation
              )}
            </div>

            <div style={{ marginTop: '15px', fontSize: '12px', color: '#666' }}>
              <strong>Note:</strong> AI explanations are generated by Ollama AI service at ai.cloudflex.tr
              and should be used as guidance only. Always verify critical information.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
