import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useNavigate } from 'react-router-dom'
import { safeArray } from '../lib/safe'

export default function Servers() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const pageSize = 20
  const navigate = useNavigate()

  // Fetch servers with current metrics
  const { data: servers, isLoading } = useQuery({
    queryKey: ['servers', page, search, statusFilter],
    queryFn: () => api.get('/v1/servers', {
      params: {
        page,
        size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined
      }
    }),
    refetchInterval: 30000
  })

  const handleSearch = () => {
    setPage(0)
  }

  const handleRowClick = (hostname: string) => {
    navigate(`/servers/${hostname}`)
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'online':
      case 'active':
        return '#28a745'
      case 'offline':
        return '#dc3545'
      case 'warning':
        return '#ffc107'
      default:
        return '#6c757d'
    }
  }

  const getUsageColor = (value: number) => {
    if (value >= 90) return '#dc3545'
    if (value >= 75) return '#ffc107'
    return '#28a745'
  }

  return (
    <div>
      <h2>Servers</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Monitor all discovered servers and agents with real-time metrics
      </p>

      {/* Search and Filters */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '15px', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Search
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by hostname, IP, or OS..."
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
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}
            >
              <option value="">All</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
              <option value="warning">Warning</option>
            </select>
          </div>

          <button
            onClick={handleSearch}
            style={{
              padding: '8px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              height: '36px'
            }}
          >
            Search
          </button>
        </div>
      </div>

      {/* Servers Table */}
      <div className="card">
        <h3>
          Servers ({safeArray(servers?.data).length} of {servers?.total || 0})
          {isLoading && <span style={{ marginLeft: '10px', color: '#999' }}>Loading...</span>}
        </h3>

        <div style={{ overflowX: 'auto', marginTop: '15px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Hostname</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>IP Address</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>OS</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>CPU %</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Memory %</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Licensed</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {safeArray(servers?.data).map((server: any) => (
                <tr
                  key={server.id}
                  onClick={() => handleRowClick(server.hostname)}
                  style={{
                    borderBottom: '1px solid #eee',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td style={{ padding: '12px', fontWeight: 'bold', fontFamily: 'monospace' }}>
                    {server.hostname}
                  </td>
                  <td style={{ padding: '12px', fontFamily: 'monospace', color: '#666' }}>
                    {server.ip_address || server.ip}
                  </td>
                  <td style={{ padding: '12px' }}>
                    {server.os || server.os_info || '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: getUsageColor(server.cpu_percent || 0),
                      color: 'white',
                      fontWeight: 'bold',
                      fontSize: '13px'
                    }}>
                      {server.cpu_percent?.toFixed(1) || '0.0'}%
                    </span>
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: getUsageColor(server.mem_percent || 0),
                      color: 'white',
                      fontWeight: 'bold',
                      fontSize: '13px'
                    }}>
                      {server.mem_percent?.toFixed(1) || '0.0'}%
                    </span>
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: getStatusColor(server.status),
                      color: 'white',
                      fontSize: '11px',
                      fontWeight: 'bold'
                    }}>
                      {server.status || 'ONLINE'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {server.licensed ? (
                      <span style={{ color: '#28a745', fontWeight: 'bold' }}>✓</span>
                    ) : (
                      <span style={{ color: '#dc3545', fontWeight: 'bold' }}>✗</span>
                    )}
                  </td>
                  <td style={{ padding: '12px', fontSize: '13px', color: '#666' }}>
                    {server.last_seen ? new Date(server.last_seen).toLocaleString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(!servers?.data || servers.data.length === 0) && !isLoading && (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
              No servers found
            </div>
          )}
        </div>

        {/* Pagination */}
        {servers?.data && servers.data.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
            <div style={{ fontSize: '14px', color: '#666' }}>
              Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, servers.total || 0)} of {servers.total || 0}
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
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
              <span style={{ fontSize: '14px' }}>Page {page + 1}</span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={servers.data.length < pageSize || (page + 1) * pageSize >= (servers.total || 0)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: (servers.data.length < pageSize || (page + 1) * pageSize >= (servers.total || 0)) ? '#ccc' : '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: (servers.data.length < pageSize || (page + 1) * pageSize >= (servers.total || 0)) ? 'not-allowed' : 'pointer'
                }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
