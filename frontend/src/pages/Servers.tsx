import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export default function Servers() {
  const { data: servers } = useQuery({
    queryKey: ['servers'],
    queryFn: () => api.get('/discovery/agents')
  })

  return (
    <div>
      <h2>Servers</h2>
      <table>
        <thead>
          <tr>
            <th>Hostname</th>
            <th>IP Address</th>
            <th>OS</th>
            <th>Status</th>
            <th>Licensed</th>
            <th>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {servers?.data?.map((server: any) => (
            <tr key={server.id}>
              <td>{server.hostname}</td>
              <td>{server.ip_address}</td>
              <td>{server.os}</td>
              <td><span className="badge info">Active</span></td>
              <td>{server.licensed ? 'Yes' : 'No'}</td>
              <td>{new Date(server.last_seen).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
