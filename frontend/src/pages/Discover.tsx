import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '../lib/api'

export default function Discover() {
  const queryClient = useQueryClient()
  const [selectedAgent, setSelectedAgent] = useState<any>(null)

  // Fetch agents
  const { data: agents } = useQuery({
    queryKey: ['discover-agents'],
    queryFn: () => api.get('/v1/discovery/agents'),
    refetchInterval: 30000
  })

  // License bind mutation
  const licenseMutation = useMutation({
    mutationFn: ({ agentId, licensed }: { agentId: number; licensed: boolean }) =>
      api.patch(`/v1/discovery/agents/${agentId}/license`, { licensed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discover-agents'] })
      alert('License status updated successfully')
    }
  })

  // Config update mutation
  const configMutation = useMutation({
    mutationFn: ({ agentId, config }: { agentId: number; config: any }) =>
      api.patch(`/v1/discovery/agents/${agentId}/config`, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discover-agents'] })
      setSelectedAgent(null)
      alert('Configuration updated successfully')
    }
  })

  const handleLicenseBind = (agentId: number, licensed: boolean) => {
    if (confirm(`Are you sure you want to ${licensed ? 'bind' : 'unbind'} license for this agent?`)) {
      licenseMutation.mutate({ agentId, licensed })
    }
  }

  const handleConfigUpdate = (agentId: number, ignoreLogs: boolean, ignoreAlerts: boolean) => {
    configMutation.mutate({
      agentId,
      config: {
        ignore_logs: ignoreLogs,
        ignore_alerts: ignoreAlerts
      }
    })
  }

  return (
    <div>
      <h2>Agent Discovery</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Manage discovered agents, bind licenses, and configure collection settings
      </p>

      {/* Agent List */}
      <div className="card">
        <h3>Discovered Agents ({agents?.data?.length || 0})</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Hostname</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>IP Address</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>OS</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Licensed</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Ignore Logs</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Ignore Alerts</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Last Seen</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {agents?.data?.map((agent: any) => (
                <tr key={agent.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>{agent.hostname}</td>
                  <td style={{ padding: '8px' }}>{agent.ip_address}</td>
                  <td style={{ padding: '8px' }}>{agent.os}</td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: agent.licensed ? '#28a745' : '#6c757d',
                      color: 'white'
                    }}>
                      {agent.licensed ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td style={{ padding: '8px' }}>
                    {agent.ignore_logs ? 'Yes' : 'No'}
                  </td>
                  <td style={{ padding: '8px' }}>
                    {agent.ignore_alerts ? 'Yes' : 'No'}
                  </td>
                  <td style={{ padding: '8px' }}>
                    {agent.last_seen ? new Date(agent.last_seen).toLocaleString() : 'Never'}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <button
                      onClick={() => handleLicenseBind(agent.id, !agent.licensed)}
                      style={{
                        padding: '4px 8px',
                        marginRight: '5px',
                        fontSize: '12px',
                        backgroundColor: agent.licensed ? '#dc3545' : '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {agent.licensed ? 'Unbind' : 'Bind'}
                    </button>
                    <button
                      onClick={() => setSelectedAgent(agent)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '12px',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Config
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Config Modal */}
      {selectedAgent && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ width: '500px', maxWidth: '90%' }}>
            <h3>Configure Agent: {selectedAgent.hostname}</h3>
            <form onSubmit={(e) => {
              e.preventDefault()
              const form = e.target as HTMLFormElement
              const formData = new FormData(form)
              handleConfigUpdate(
                selectedAgent.id,
                formData.get('ignore_logs') === 'on',
                formData.get('ignore_alerts') === 'on'
              )
            }}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    name="ignore_logs"
                    defaultChecked={selectedAgent.ignore_logs}
                    style={{ marginRight: '8px' }}
                  />
                  <span>Ignore Logs (stop sending logs from this agent)</span>
                </label>
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    name="ignore_alerts"
                    defaultChecked={selectedAgent.ignore_alerts}
                    style={{ marginRight: '8px' }}
                  />
                  <span>Ignore Alerts (don't trigger alerts for this agent)</span>
                </label>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setSelectedAgent(null)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
