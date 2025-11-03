import api from './api'

export interface ESSearchParams {
  tenant?: string
  query?: string
  from?: string
  to?: string
  size?: number
  page?: number
  severity?: string
  host?: string
  index?: string
}

export async function esSearch(params: ESSearchParams): Promise<any> {
  const {
    tenant,
    query,
    from = 'now-1h',
    to = 'now',
    size = 100,
    page = 0,
    severity,
    host,
    index = 'logs-*'
  } = params

  // Build ES query
  const must: any[] = []

  // Time range
  must.push({
    range: {
      '@timestamp': {
        gte: from,
        lte: to
      }
    }
  })

  // Filters
  if (tenant) {
    must.push({ match: { tenant_id: tenant } })
  }
  if (host) {
    must.push({ match: { host } })
  }
  if (severity) {
    must.push({ match: { level: severity } })
  }

  // KQL-like query parsing
  if (query) {
    if (query.includes(':')) {
      // Parse field:value syntax
      const parts = query.split('AND').map(p => p.trim())
      parts.forEach(part => {
        if (part.includes(':')) {
          const [field, value] = part.split(':').map(s => s.trim().replace(/['"]/g, ''))
          must.push({ match: { [field]: value } })
        }
      })
    } else {
      // Simple text search
      must.push({
        multi_match: {
          query,
          fields: ['message', 'level', 'host', 'source'],
          type: 'best_fields'
        }
      })
    }
  }

  const esQuery = {
    query: { bool: { must } },
    sort: [{ '@timestamp': { order: 'desc' } }],
    size,
    from: page * size
  }

  // Call backend ES passthrough endpoint
  const response = await api.post('/es/search', {
    index,
    body: esQuery
  })

  return response.data
}
