export default function Settings() {
  return (
    <div>
      <h2>Settings</h2>
      <div className="card">
        <h3>Security</h3>
        <p>TLS/mTLS configuration and certificate upload</p>
      </div>
      <div className="card">
        <h3>Notifications</h3>
        <p>Configure notification channels: Email, Slack, Teams, Telegram, WhatsApp</p>
      </div>
      <div className="card">
        <h3>Backup</h3>
        <p>S3 backup configuration</p>
      </div>
      <div className="card">
        <h3>AI Service</h3>
        <p>Ollama AI service token configuration</p>
      </div>
    </div>
  )
}
