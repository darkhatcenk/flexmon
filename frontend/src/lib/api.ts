import axios, { AxiosInstance } from 'axios'

// Fallback baseURL: use "/api" which Nginx proxies to backend
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

// Create axios instance with named export
export const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('flexmon_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('flexmon_token')
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Helper functions for auth and tenant management
export function setAuth(token?: string) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    localStorage.setItem('flexmon_token', token)
  } else {
    delete api.defaults.headers.common['Authorization']
    localStorage.removeItem('flexmon_token')
  }
}

export function setTenant(tenantId?: string) {
  if (tenantId) {
    api.defaults.headers.common['X-Tenant-Id'] = tenantId
  } else {
    delete api.defaults.headers.common['X-Tenant-Id']
  }
}

// Keep default export for backward compatibility
export default api
