import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

export default function Settings() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('security')

  // Fetch current settings
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get('/v1/settings')
  })

  // TLS/mTLS mutation
  const tlsMutation = useMutation({
    mutationFn: (data: any) => api.post('/v1/settings/tls', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      alert('TLS settings updated successfully')
    }
  })

  // Notification channel mutation
  const notificationMutation = useMutation({
    mutationFn: (data: any) => api.post('/v1/settings/notifications', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      alert('Notification settings updated successfully')
    }
  })

  // Backup settings mutation
  const backupMutation = useMutation({
    mutationFn: (data: any) => api.post('/v1/settings/backup', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      alert('Backup settings updated successfully')
    }
  })

  // AI settings mutation
  const aiMutation = useMutation({
    mutationFn: (data: any) => api.post('/v1/settings/ai', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      alert('AI settings updated successfully')
    }
  })

  return (
    <div>
      <h2>Settings</h2>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #ddd' }}>
        {['security', 'notifications', 'backup', 'ai'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === tab ? '2px solid #007bff' : 'none',
              color: activeTab === tab ? '#007bff' : '#666',
              cursor: 'pointer',
              fontWeight: activeTab === tab ? 'bold' : 'normal',
              textTransform: 'capitalize'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="card">
          <h3>TLS/mTLS Configuration</h3>
          <form onSubmit={(e) => {
            e.preventDefault()
            const formData = new FormData(e.target as HTMLFormElement)
            tlsMutation.mutate({
              tls_enabled: formData.get('tls_enabled') === 'on',
              mtls_enabled: formData.get('mtls_enabled') === 'on'
            })
          }}>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="tls_enabled"
                  defaultChecked={settings?.data?.tls_enabled}
                  style={{ marginRight: '10px' }}
                />
                <span>Enable TLS</span>
              </label>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                Enable Transport Layer Security for encrypted connections
              </p>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="mtls_enabled"
                  defaultChecked={settings?.data?.mtls_enabled}
                  style={{ marginRight: '10px' }}
                />
                <span>Enable mTLS (Mutual TLS)</span>
              </label>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                Require client certificates for authentication
              </p>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Upload Certificate
              </label>
              <input
                type="file"
                accept=".pem,.crt,.key"
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                Upload PEM format certificates (.pem, .crt, .key)
              </p>
            </div>

            <button
              type="submit"
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save TLS Settings
            </button>
          </form>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="card">
          <h3>Notification Channels</h3>
          <form onSubmit={(e) => {
            e.preventDefault()
            const formData = new FormData(e.target as HTMLFormElement)
            const channels: any = {}

            if (formData.get('email_enabled') === 'on') {
              channels.email = {
                smtp_host: formData.get('smtp_host'),
                smtp_port: formData.get('smtp_port'),
                from_address: formData.get('from_address'),
                username: formData.get('smtp_username'),
                password: formData.get('smtp_password')
              }
            }

            if (formData.get('slack_enabled') === 'on') {
              channels.slack = {
                webhook_url: formData.get('slack_webhook')
              }
            }

            if (formData.get('teams_enabled') === 'on') {
              channels.teams = {
                webhook_url: formData.get('teams_webhook')
              }
            }

            if (formData.get('telegram_enabled') === 'on') {
              channels.telegram = {
                bot_token: formData.get('telegram_token'),
                chat_id: formData.get('telegram_chat')
              }
            }

            if (formData.get('whatsapp_enabled') === 'on') {
              channels.whatsapp = {
                access_token: formData.get('whatsapp_token'),
                phone_number_id: formData.get('whatsapp_phone')
              }
            }

            notificationMutation.mutate({ channels })
          }}>
            {/* Email/SMTP */}
            <div style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #ddd' }}>
              <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px', cursor: 'pointer' }}>
                <input type="checkbox" name="email_enabled" defaultChecked style={{ marginRight: '10px' }} />
                <strong>Email/SMTP</strong>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginLeft: '30px' }}>
                <input type="text" name="smtp_host" placeholder="SMTP Host" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="text" name="smtp_port" placeholder="SMTP Port (587)" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="email" name="from_address" placeholder="From Address" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="text" name="smtp_username" placeholder="Username" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="password" name="smtp_password" placeholder="Password" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
              </div>
            </div>

            {/* Slack */}
            <div style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #ddd' }}>
              <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px', cursor: 'pointer' }}>
                <input type="checkbox" name="slack_enabled" style={{ marginRight: '10px' }} />
                <strong>Slack</strong>
              </label>
              <input type="text" name="slack_webhook" placeholder="Webhook URL" style={{ width: '100%', marginLeft: '30px', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
            </div>

            {/* Microsoft Teams */}
            <div style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #ddd' }}>
              <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px', cursor: 'pointer' }}>
                <input type="checkbox" name="teams_enabled" style={{ marginRight: '10px' }} />
                <strong>Microsoft Teams</strong>
              </label>
              <input type="text" name="teams_webhook" placeholder="Webhook URL" style={{ width: '100%', marginLeft: '30px', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
            </div>

            {/* Telegram */}
            <div style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #ddd' }}>
              <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px', cursor: 'pointer' }}>
                <input type="checkbox" name="telegram_enabled" style={{ marginRight: '10px' }} />
                <strong>Telegram</strong>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginLeft: '30px' }}>
                <input type="text" name="telegram_token" placeholder="Bot Token" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="text" name="telegram_chat" placeholder="Chat ID" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
              </div>
            </div>

            {/* WhatsApp */}
            <div style={{ marginBottom: '30px', paddingBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px', cursor: 'pointer' }}>
                <input type="checkbox" name="whatsapp_enabled" style={{ marginRight: '10px' }} />
                <strong>WhatsApp Business API</strong>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginLeft: '30px' }}>
                <input type="text" name="whatsapp_token" placeholder="Access Token" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
                <input type="text" name="whatsapp_phone" placeholder="Phone Number ID" style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }} />
              </div>
            </div>

            <button
              type="submit"
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save Notification Settings
            </button>
          </form>
        </div>
      )}

      {/* Backup Tab */}
      {activeTab === 'backup' && (
        <div className="card">
          <h3>S3 Backup Configuration</h3>
          <form onSubmit={(e) => {
            e.preventDefault()
            const formData = new FormData(e.target as HTMLFormElement)
            backupMutation.mutate({
              enabled: formData.get('backup_enabled') === 'on',
              s3_bucket: formData.get('s3_bucket'),
              s3_path: formData.get('s3_path'),
              s3_region: formData.get('s3_region'),
              access_key: formData.get('access_key'),
              secret_key: formData.get('secret_key')
            })
          }}>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="backup_enabled"
                  defaultChecked={settings?.data?.backup_enabled}
                  style={{ marginRight: '10px' }}
                />
                <span>Enable Automated S3 Backups</span>
              </label>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  S3 Bucket
                </label>
                <input
                  type="text"
                  name="s3_bucket"
                  placeholder="my-backup-bucket"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  S3 Path (per-tenant)
                </label>
                <input
                  type="text"
                  name="s3_path"
                  placeholder="/backups/{tenant_id}/"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  AWS Region
                </label>
                <input
                  type="text"
                  name="s3_region"
                  placeholder="us-east-1"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Access Key
                </label>
                <input
                  type="text"
                  name="access_key"
                  placeholder="AWS Access Key"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Secret Key
                </label>
                <input
                  type="password"
                  name="secret_key"
                  placeholder="AWS Secret Key"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>

            <button
              type="submit"
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save Backup Settings
            </button>
          </form>
        </div>
      )}

      {/* AI Tab */}
      {activeTab === 'ai' && (
        <div className="card">
          <h3>AI Service Configuration</h3>
          <p style={{ color: '#666', marginBottom: '20px' }}>
            Configure Ollama AI service for alert explanations and insights
          </p>
          <form onSubmit={(e) => {
            e.preventDefault()
            const formData = new FormData(e.target as HTMLFormElement)
            aiMutation.mutate({
              enabled: formData.get('ai_enabled') === 'on',
              api_url: formData.get('ai_url'),
              api_token: formData.get('ai_token'),
              model: formData.get('ai_model')
            })
          }}>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="ai_enabled"
                  defaultChecked={settings?.data?.ai_enabled}
                  style={{ marginRight: '10px' }}
                />
                <span>Enable AI Explanations</span>
              </label>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                AI API URL (ai.cloudflex.tr)
              </label>
              <input
                type="text"
                name="ai_url"
                placeholder="https://ai.cloudflex.tr/api"
                defaultValue="https://ai.cloudflex.tr/api"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                API Token
              </label>
              <input
                type="password"
                name="ai_token"
                placeholder="Enter API token"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Model
              </label>
              <select
                name="ai_model"
                defaultValue="llama2"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value="llama2">Llama 2</option>
                <option value="llama3">Llama 3</option>
                <option value="mistral">Mistral</option>
                <option value="codellama">Code Llama</option>
              </select>
            </div>

            <button
              type="submit"
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save AI Settings
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
