import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { esSearch } from '../lib/es'

export default function Logs() {
  const [query, setQuery] = useState('')
  const [tenant, setTenant] = useState('')
  const [host, setHost] = useState('')
  const [severity, setSeverity] = useState('')
  const [timeRange, setTimeRange] = useState('1h')
  const [page, setPage] = useState(0)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const pageSize = 100

  // Fetch logs from Elasticsearch via passthrough
  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['logs', query, tenant, host, severity, timeRange, page],
    queryFn: () => esSearch({
      tenant: tenant || undefined,
      query: query || undefined,
      host: host || undefined,
      severity: severity || undefined,
      from: `now-${timeRange}`,
      to: 'now',
      size: pageSize,
      page
    }),
    refetchInterval: 30000
  })

  const handleSearch = () => {
    setPage(0)
    refetch()
  }

  const severityColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'critical':
        return '#dc3545'
      case 'warning':
      case 'warn':
        return '#ffc107'
      case 'info':
        return '#17a2b8'
      case 'debug':
        return '#6c757d'
      default:
        return '#6c757d'
    }
  }

  const toggleRow = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id)
  }

  return (
    <div>
      <h2>Logs</h2>

      {/* Search and Filters */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>Search & Filters</h3>

        {/* KQL-like Query */}
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Query (KQL-like: field:value AND field2:value2 OR simple text)
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder='e.g., message:"error" AND service:api OR simple search'
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

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

          {/* Host Filter */}
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Host
            </label>
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="Filter by host"
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
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
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
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last hour</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
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

      {/* Log Results */}
      <div className="card">
        <h3>
          Results ({logs?.hits?.hits?.length || 0} logs)
          {isLoading && <span style={{ marginLeft: '10px', color: '#999' }}>Loading...</span>}
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '15px' }}>
          {logs?.hits?.hits?.map((hit: any, idx: number) => {
            const log = hit._source
            const isExpanded = expandedRow === hit._id
            return (
              <div
                key={hit._id || idx}
                style={{
                  padding: '12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  borderLeft: `4px solid ${severityColor(log.level)}`,
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
                onClick={() => toggleRow(hit._id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div>
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: '3px',
                      backgroundColor: severityColor(log.level),
                      color: 'white',
                      fontSize: '11px',
                      marginRight: '8px'
                    }}>
                      {log.level || 'INFO'}
                    </span>
                    <span style={{ color: '#666' }}>
                      {log.host || 'unknown'}
                    </span>
                    {log.tenant_id && (
                      <span style={{ color: '#999', marginLeft: '8px' }}>
                        [{log.tenant_id}]
                      </span>
                    )}
                  </div>
                  <span style={{ color: '#888', fontSize: '12px' }}>
                    {new Date(log['@timestamp'] || log.timestamp).toLocaleString()}
                  </span>
                </div>
                <div style={{ color: '#333' }}>
                  {log.message}
                </div>
                {log.source && (
                  <div style={{ color: '#999', fontSize: '11px', marginTop: '4px' }}>
                    Source: {log.source}
                  </div>
                )}

                {/* Expanded JSON view */}
                {isExpanded && (
                  <div style={{
                    marginTop: '10px',
                    padding: '10px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    overflow: 'auto',
                    maxHeight: '300px'
                  }}>
                    <pre style={{ margin: 0, fontSize: '11px' }}>
                      {JSON.stringify(log, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )
          })}

          {(!logs?.hits?.hits || logs.hits.hits.length === 0) && !isLoading && (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
              No logs found matching your search criteria
            </div>
          )}
        </div>

        {/* Pagination */}
        {logs?.hits?.hits && logs.hits.hits.length > 0 && (
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
              disabled={logs.hits.hits.length < pageSize}
              style={{
                padding: '8px 16px',
                backgroundColor: logs.hits.hits.length < pageSize ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: logs.hits.hits.length < pageSize ? 'not-allowed' : 'pointer'
              }}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
