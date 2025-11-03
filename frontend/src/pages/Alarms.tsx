import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export default function Alarms() {
  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.get('/alerts')
  })

  return (
    <div>
      <h2>Alarms</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Severity</th>
            <th>Host</th>
            <th>Message</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {alerts?.data?.map((alert: any) => (
            <tr key={alert.id}>
              <td>{new Date(alert.triggered_at).toLocaleString()}</td>
              <td><span className={`badge ${alert.severity}`}>{alert.severity}</span></td>
              <td>{alert.host}</td>
              <td>{alert.message}</td>
              <td><button>Acknowledge</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
