import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { esSearch } from '../lib/es'

export default function PlatformLogs() {
  const [query, setQuery] = useState('')
  const [user, setUser] = useState('')
  const [action, setAction] = useState('')
  const [timeRange, setTimeRange] = useState('24h')
  const [page, setPage] = useState(0)
  const pageSize = 50

  // Fetch platform audit logs from ES
  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['platform-logs', query, user, action, timeRange, page],
    queryFn: () => esSearch({
      index: 'platform-logs-*',
      query: query || undefined,
      from: `now-${timeRange}`,
      to: 'now',
      size: pageSize,
      page,
      host: user || undefined
    }),
    refetchInterval: 60000
  })

  const handleSearch = () => {
    setPage(0)
    refetch()
  }

  return (
    <div>
      <h2>Platform Audit Logs</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        View and search platform-level audit trail and system events
      </p>

      {/* Search and Filters */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>Search & Filters</h3>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Search Query
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search logs..."
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              User
            </label>
            <input
              type="text"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="Filter by user"
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Action
            </label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            >
              <option value="">All Actions</option>
              <option value="login">Login</option>
              <option value="logout">Logout</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="config">Configuration Change</option>
            </select>
          </div>

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

      {/* Log Results */}
      <div className="card">
        <h3>
          Audit Trail ({logs?.hits?.hits?.length || 0} logs)
          {isLoading && <span style={{ marginLeft: '10px', color: '#999' }}>Loading...</span>}
        </h3>

        <div style={{ overflowX: 'auto', marginTop: '15px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Timestamp</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>User</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Action</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Resource</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Details</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>IP</th>
              </tr>
            </thead>
            <tbody>
              {logs?.hits?.hits?.map((hit: any, idx: number) => {
                const log = hit._source
                return (
                  <tr key={hit._id || idx} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '8px', whiteSpace: 'nowrap' }}>
                      {new Date(log['@timestamp'] || log.timestamp).toLocaleString()}
                    </td>
                    <td style={{ padding: '8px' }}>{log.user || log.username || 'system'}</td>
                    <td style={{ padding: '8px' }}>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '3px',
                        backgroundColor: log.action === 'delete' ? '#dc3545' :
                          log.action === 'create' ? '#28a745' :
                          log.action === 'update' ? '#ffc107' : '#17a2b8',
                        color: 'white',
                        fontSize: '11px'
                      }}>
                        {log.action || log.level}
                      </span>
                    </td>
                    <td style={{ padding: '8px' }}>{log.resource || log.entity || '-'}</td>
                    <td style={{ padding: '8px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.message || log.details || '-'}
                    </td>
                    <td style={{ padding: '8px' }}>{log.ip_address || log.ip || '-'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {(!logs?.hits?.hits || logs.hits.hits.length === 0) && !isLoading && (
          <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
            No audit logs found
          </div>
        )}

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
