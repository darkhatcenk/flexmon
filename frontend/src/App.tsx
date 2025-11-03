import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Servers from './pages/Servers'
import Logs from './pages/Logs'
import Alarms from './pages/Alarms'
import Users from './pages/Users'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="sidebar">
          <h1>FlexMON</h1>
          <ul>
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/servers">Servers</Link></li>
            <li><Link to="/logs">Logs</Link></li>
            <li><Link to="/alarms">Alarms</Link></li>
            <li><Link to="/users">Users</Link></li>
            <li><Link to="/settings">Settings</Link></li>
          </ul>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/servers" element={<Servers />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/alarms" element={<Alarms />} />
            <Route path="/users" element={<Users />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
