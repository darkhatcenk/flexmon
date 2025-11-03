import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export default function Dashboard() {
  const { data: metrics } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => api.get('/metrics/summary'),
    refetchInterval: 30000
  })

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="dashboard-grid">
        <div className="card">
          <h3>CPU Usage</h3>
          <div style={{fontSize: '32px', fontWeight: 'bold'}}>
            {metrics?.cpu_avg || '-'}%
          </div>
        </div>
        <div className="card">
          <h3>Memory Usage</h3>
          <div style={{fontSize: '32px', fontWeight: 'bold'}}>
            {metrics?.memory_avg || '-'}%
          </div>
        </div>
        <div className="card">
          <h3>Active Servers</h3>
          <div style={{fontSize: '32px', fontWeight: 'bold'}}>
            {metrics?.server_count || '0'}
          </div>
        </div>
        <div className="card">
          <h3>Active Alerts</h3>
          <div style={{fontSize: '32px', fontWeight: 'bold'}}>
            {metrics?.alert_count || '0'}
          </div>
        </div>
      </div>
      <div className="card">
        <h3>Recent Activity</h3>
        <p>Real-time monitoring dashboard with ApexCharts integration</p>
      </div>
    </div>
  )
}
