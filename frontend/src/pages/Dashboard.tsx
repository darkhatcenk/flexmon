import { useQuery } from '@tanstack/react-query'
import Chart from 'react-apexcharts'
import { ApexOptions } from 'apexcharts'
import { api } from '../lib/api'
import { Link } from 'react-router-dom'
import NoData from '../components/NoData'
import { safeArray, toNumber, debugData } from '../lib/safe'

export default function Dashboard() {
  // Fetch top 10 servers by metric
  const { data: topCPU } = useQuery({
    queryKey: ['top-cpu'],
    queryFn: () => api.get('/v1/metrics/top?metric=cpu&limit=10'),
    refetchInterval: 30000
  })

  const { data: topMemory } = useQuery({
    queryKey: ['top-memory'],
    queryFn: () => api.get('/v1/metrics/top?metric=memory&limit=10'),
    refetchInterval: 30000
  })

  const { data: topNetwork } = useQuery({
    queryKey: ['top-network'],
    queryFn: () => api.get('/v1/metrics/top?metric=network&limit=10'),
    refetchInterval: 30000
  })

  const { data: topDisk } = useQuery({
    queryKey: ['top-disk'],
    queryFn: () => api.get('/v1/metrics/top?metric=disk&limit=10'),
    refetchInterval: 30000
  })

  // Fetch server list
  const { data: servers } = useQuery({
    queryKey: ['servers'],
    queryFn: () => api.get('/v1/discovery/agents'),
    refetchInterval: 60000
  })

  // Fetch last 20 alarms
  const { data: recentAlarms } = useQuery({
    queryKey: ['recent-alarms'],
    queryFn: () => api.get('/v1/alerts?limit=20&resolved=false'),
    refetchInterval: 15000
  })

  const createPieChart = (data: any[], title: string, unit: string): ApexOptions => {
    const safeData = safeArray(data)
    const labels = safeData.map(d => String(d?.host || 'unknown'))
    const values = safeData.map(d => toNumber(d?.value, 0))

    return {
      chart: { type: 'pie', height: 300 },
      title: { text: title, align: 'center' },
      labels,
      series: values,
      legend: { position: 'bottom' },
      dataLabels: {
        enabled: true,
        formatter: (val: number) => `${toNumber(val, 0).toFixed(1)}${unit}`
      },
      tooltip: { y: { formatter: (val: number) => `${toNumber(val, 0).toFixed(2)}${unit}` } }
    }
  }

  const renderChart = (queryData: any, title: string, unit: string, endpoint: string) => {
    const rawData = queryData?.data
    const safeData = safeArray(rawData)
    const sanitized = safeData.filter((d: any) => d && d.host && toNumber(d.value, -1) >= 0)

    if (sanitized.length === 0) {
      debugData({
        component: 'Dashboard',
        endpoint,
        reason: 'empty-or-invalid-data',
        details: { originalLength: safeData.length, sanitizedLength: 0 }
      })
      return <NoData reason="no-valid-data" height={300} />
    }

    const series = sanitized.map((d: any) => toNumber(d.value, 0))
    return (
      <Chart
        options={createPieChart(sanitized, title, unit)}
        series={series}
        type="pie"
        height={300}
      />
    )
  }

  return (
    <div style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 80px)' }}>
      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <h2>Dashboard</h2>

        {/* Top 10 Charts */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div className="card">
            {renderChart(topCPU, 'Top 10 CPU Usage', '%', '/v1/metrics/top?metric=cpu')}
          </div>

          <div className="card">
            {renderChart(topMemory, 'Top 10 Memory Usage', '%', '/v1/metrics/top?metric=memory')}
          </div>

          <div className="card">
            {renderChart(topNetwork, 'Top 10 Network Traffic', ' MB/s', '/v1/metrics/top?metric=network')}
          </div>

          <div className="card">
            {renderChart(topDisk, 'Top 10 Disk Usage', '%', '/v1/metrics/top?metric=disk')}
          </div>
        </div>

        {/* Server List */}
        <div className="card">
          <h3>Servers ({safeArray(servers?.data).length})</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Hostname</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Status</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>OS</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Licensed</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Last Seen</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {safeArray(servers?.data).map((server: any) => (
                  <tr key={server.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '8px' }}>
                      <Link to={`/servers/${server.hostname}`} style={{ color: '#007bff', textDecoration: 'none' }}>
                        {server.hostname}
                      </Link>
                    </td>
                    <td style={{ padding: '8px' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        backgroundColor: server.licensed ? '#28a745' : '#ffc107',
                        color: 'white'
                      }}>
                        {server.licensed ? 'Active' : 'Unlicensed'}
                      </span>
                    </td>
                    <td style={{ padding: '8px' }}>{server.os || 'N/A'}</td>
                    <td style={{ padding: '8px' }}>{server.licensed ? 'Yes' : 'No'}</td>
                    <td style={{ padding: '8px' }}>
                      {server.last_seen ? new Date(server.last_seen).toLocaleString() : 'Never'}
                    </td>
                    <td style={{ padding: '8px' }}>
                      <Link to={`/servers/${server.hostname}`} style={{ color: '#007bff' }}>
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Right Panel - Last 20 Alarms */}
      <div style={{ width: '350px', backgroundColor: '#f8f9fa', padding: '20px', overflowY: 'auto' }}>
        <h3>Recent Alarms</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {safeArray(recentAlarms?.data).map((alarm: any) => (
            <div
              key={alarm.id}
              className="card"
              style={{
                padding: '12px',
                borderLeft: `4px solid ${
                  alarm.severity === 'critical' ? '#dc3545' :
                  alarm.severity === 'error' ? '#fd7e14' :
                  alarm.severity === 'warning' ? '#ffc107' : '#17a2b8'
                }`,
                fontSize: '14px'
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                {alarm.rule_name || 'Alert'}
              </div>
              <div style={{ color: '#666', fontSize: '12px', marginBottom: '4px' }}>
                {alarm.host}
              </div>
              <div style={{ fontSize: '12px', color: '#888' }}>
                {new Date(alarm.triggered_at).toLocaleString()}
              </div>
              <div style={{ marginTop: '8px', fontSize: '12px' }}>
                {alarm.message}
              </div>
            </div>
          ))}
          {(!recentAlarms?.data || recentAlarms.data.length === 0) && (
            <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
              No active alarms
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
