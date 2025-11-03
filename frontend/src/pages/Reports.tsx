import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import api from '../lib/api'
import Chart from 'react-apexcharts'
import { ApexOptions } from 'apexcharts'

export default function Reports() {
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7)) // YYYY-MM
  const [selectedTenant, setSelectedTenant] = useState('')

  // Fetch monthly summary
  const { data: summary } = useQuery({
    queryKey: ['reports-summary', month, selectedTenant],
    queryFn: () => api.get(`/v1/reports/monthly?month=${month}${selectedTenant ? `&tenant_id=${selectedTenant}` : ''}`),
    refetchInterval: 300000 // 5 min
  })

  // Fetch tenant list
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get('/v1/tenants')
  })

  // Fetch alarm counts
  const { data: alarmCounts } = useQuery({
    queryKey: ['alarm-counts', month],
    queryFn: () => api.get(`/v1/reports/alarms?month=${month}`)
  })

  const chartOptions: ApexOptions = {
    chart: { type: 'bar', height: 300 },
    xaxis: {
      categories: summary?.data?.map((d: any) => d.tenant_id) || []
    },
    title: { text: 'Monthly Resource Usage by Tenant', align: 'center' }
  }

  return (
    <div>
      <h2>Reports</h2>

      {/* Filters */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3>Filters</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Month
            </label>
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Tenant (optional)
            </label>
            <select
              value={selectedTenant}
              onChange={(e) => setSelectedTenant(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="">All Tenants</option>
              {tenants?.data?.map((t: any) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Summary Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '20px' }}>
        <div className="card">
          <Chart
            options={chartOptions}
            series={[{
              name: 'Avg CPU %',
              data: summary?.data?.map((d: any) => d.avg_cpu) || []
            }]}
            type="bar"
            height={300}
          />
        </div>

        <div className="card">
          <Chart
            options={{...chartOptions, title: { text: 'Monthly Memory Usage by Tenant' }}}
            series={[{
              name: 'Avg Memory %',
              data: summary?.data?.map((d: any) => d.avg_memory) || []
            }]}
            type="bar"
            height={300}
          />
        </div>

        <div className="card">
          <Chart
            options={{...chartOptions, title: { text: 'Monthly Network Usage by Tenant' }}}
            series={[{
              name: 'Total Network (GB)',
              data: summary?.data?.map((d: any) => d.total_network_gb) || []
            }]}
            type="bar"
            height={300}
          />
        </div>

        <div className="card">
          <Chart
            options={{...chartOptions, title: { text: 'Monthly Disk Usage by Tenant' }}}
            series={[{
              name: 'Avg Disk %',
              data: summary?.data?.map((d: any) => d.avg_disk) || []
            }]}
            type="bar"
            height={300}
          />
        </div>
      </div>

      {/* Alarm Summary Table */}
      <div className="card">
        <h3>Alarm Summary</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '8px', textAlign: 'left' }}>Tenant</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Critical</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Error</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Warning</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Info</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {alarmCounts?.data?.map((row: any) => (
              <tr key={row.tenant_id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '8px' }}>{row.tenant_id}</td>
                <td style={{ padding: '8px', textAlign: 'right', color: '#dc3545' }}>{row.critical || 0}</td>
                <td style={{ padding: '8px', textAlign: 'right', color: '#fd7e14' }}>{row.error || 0}</td>
                <td style={{ padding: '8px', textAlign: 'right', color: '#ffc107' }}>{row.warning || 0}</td>
                <td style={{ padding: '8px', textAlign: 'right', color: '#17a2b8' }}>{row.info || 0}</td>
                <td style={{ padding: '8px', textAlign: 'right', fontWeight: 'bold' }}>{row.total || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detailed Summary Table */}
      <div className="card" style={{ marginTop: '20px' }}>
        <h3>Detailed Summary</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '8px', textAlign: 'left' }}>Tenant</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Avg CPU %</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Avg Memory %</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Avg Disk %</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Network (GB)</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Servers</th>
            </tr>
          </thead>
          <tbody>
            {summary?.data?.map((row: any) => (
              <tr key={row.tenant_id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '8px' }}>{row.tenant_id}</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{row.avg_cpu?.toFixed(2)}%</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{row.avg_memory?.toFixed(2)}%</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{row.avg_disk?.toFixed(2)}%</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{row.total_network_gb?.toFixed(2)}</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{row.server_count || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
