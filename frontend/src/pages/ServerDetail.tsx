import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import Chart from 'react-apexcharts'
import { ApexOptions } from 'apexcharts'
import { api } from '../lib/api'
import NoData from '../components/NoData'
import { safeArray, toNumber, debugData } from '../lib/safe'

export default function ServerDetail() {
  const { hostname } = useParams()

  // Fetch 1-week metrics from Timescale
  const { data: cpuData } = useQuery({
    queryKey: ['server-cpu', hostname],
    queryFn: () => api.get(`/v1/metrics/history?host=${hostname}&metric=cpu&days=7`),
    refetchInterval: 60000,
    enabled: !!hostname
  })

  const { data: memoryData } = useQuery({
    queryKey: ['server-memory', hostname],
    queryFn: () => api.get(`/v1/metrics/history?host=${hostname}&metric=memory&days=7`),
    refetchInterval: 60000,
    enabled: !!hostname
  })

  const { data: networkData } = useQuery({
    queryKey: ['server-network', hostname],
    queryFn: () => api.get(`/v1/metrics/history?host=${hostname}&metric=network&days=7`),
    refetchInterval: 60000,
    enabled: !!hostname
  })

  const { data: diskData } = useQuery({
    queryKey: ['server-disk', hostname],
    queryFn: () => api.get(`/v1/metrics/history?host=${hostname}&metric=disk&days=7`),
    refetchInterval: 60000,
    enabled: !!hostname
  })

  // Fetch running processes
  const { data: processes } = useQuery({
    queryKey: ['server-processes', hostname],
    queryFn: () => api.get(`/v1/metrics/processes?host=${hostname}`),
    refetchInterval: 30000,
    enabled: !!hostname
  })

  // Fetch recent alarms for this server
  const { data: alarms } = useQuery({
    queryKey: ['server-alarms', hostname],
    queryFn: () => api.get(`/v1/alerts?host=${hostname}&limit=10`),
    refetchInterval: 15000,
    enabled: !!hostname
  })

  const createTimeSeriesChart = (data: any[], title: string, yAxisLabel: string): ApexOptions => {
    const safeData = safeArray(data)
    const categories = safeData.map(d => d?.timestamp || new Date().toISOString())

    return {
      chart: {
        type: 'line',
        height: 300,
        zoom: { enabled: true },
        toolbar: { show: true }
      },
      title: { text: title, align: 'left' },
      xaxis: {
        type: 'datetime',
        categories
      },
      yaxis: {
        title: { text: yAxisLabel },
        min: 0,
        max: 100
      },
      stroke: { curve: 'smooth', width: 2 },
      dataLabels: { enabled: false },
      tooltip: {
        x: { format: 'dd MMM yyyy HH:mm' }
      },
      colors: ['#008FFB']
    }
  }

  const renderTimeSeriesChart = (queryData: any, title: string, yAxisLabel: string, seriesName: string, endpoint: string) => {
    const rawData = queryData?.data
    const safeData = safeArray(rawData)
    const sanitized = safeData.filter((d: any) => d && d.timestamp)
    const values = sanitized.map((d: any) => toNumber(d.value, 0))

    if (sanitized.length === 0 || values.every(v => v === 0)) {
      debugData({
        component: 'ServerDetail',
        endpoint,
        reason: 'empty-or-invalid-timeseries',
        details: { originalLength: safeData.length, sanitizedLength: sanitized.length }
      })
      return <NoData reason="no-timeseries-data" height={300} />
    }

    return (
      <Chart
        options={createTimeSeriesChart(sanitized, title, yAxisLabel)}
        series={[{ name: seriesName, data: values }]}
        type="line"
        height={300}
      />
    )
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h2>Server: {hostname}</h2>
        <p style={{ color: '#666' }}>1-week historical metrics and current status</p>
      </div>

      {/* 1-Week Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '20px' }}>
        <div className="card">
          {renderTimeSeriesChart(cpuData, 'CPU Usage (1 Week)', 'CPU %', 'CPU %', `/v1/metrics/history?host=${hostname}&metric=cpu`)}
        </div>

        <div className="card">
          {renderTimeSeriesChart(memoryData, 'Memory Usage (1 Week)', 'Memory %', 'Memory %', `/v1/metrics/history?host=${hostname}&metric=memory`)}
        </div>

        <div className="card">
          {renderTimeSeriesChart(networkData, 'Network Traffic (1 Week)', 'MB/s', 'Network', `/v1/metrics/history?host=${hostname}&metric=network`)}
        </div>

        <div className="card">
          {renderTimeSeriesChart(diskData, 'Disk Usage (1 Week)', 'Disk %', 'Disk %', `/v1/metrics/history?host=${hostname}&metric=disk`)}
        </div>
      </div>

      {/* Running Applications */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>Running Applications (Top 10 by CPU)</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>PID</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Name</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>CPU %</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Memory %</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Memory (MB)</th>
              </tr>
            </thead>
            <tbody>
              {safeArray(processes?.data).map((proc: any) => (
                <tr key={proc.pid} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>{proc.pid}</td>
                  <td style={{ padding: '8px' }}>{proc.name}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{proc.cpu_percent?.toFixed(2)}%</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{proc.memory_percent?.toFixed(2)}%</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>
                    {(proc.memory_rss / 1024 / 1024).toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Alarms */}
      <div className="card">
        <h3>Recent Alarms</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {safeArray(alarms?.data).map((alarm: any) => (
            <div
              key={alarm.id}
              style={{
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                borderLeft: `4px solid ${
                  alarm.severity === 'critical' ? '#dc3545' :
                  alarm.severity === 'error' ? '#fd7e14' :
                  alarm.severity === 'warning' ? '#ffc107' : '#17a2b8'
                }`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 'bold' }}>{alarm.rule_name}</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  backgroundColor: alarm.resolved_at ? '#28a745' : '#dc3545',
                  color: 'white'
                }}>
                  {alarm.resolved_at ? 'Resolved' : 'Active'}
                </span>
              </div>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                {alarm.message}
              </div>
              <div style={{ fontSize: '12px', color: '#888' }}>
                Triggered: {new Date(alarm.triggered_at).toLocaleString()}
                {alarm.resolved_at && ` • Resolved: ${new Date(alarm.resolved_at).toLocaleString()}`}
              </div>
            </div>
          ))}
          {(!alarms?.data || alarms.data.length === 0) && (
            <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
              No alarms for this server
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
