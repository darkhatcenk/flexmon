/**
 * Authentication store and utilities
 */

import { api } from './api'

const TOKEN_KEY = 'flexmon_token'

export interface User {
  id: number
  username: string
  email?: string
  role: 'platform_admin' | 'tenant_admin' | 'tenant_reporter'
  tenant_id?: string
  enabled: boolean
  created_at?: string
  last_login?: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
}

class AuthStore {
  private state: AuthState = {
    token: null,
    user: null,
    isAuthenticated: false
  }

  private listeners: Set<() => void> = new Set()

  constructor() {
    this.loadFromStorage()
  }

  subscribe(listener: () => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notify() {
    this.listeners.forEach(listener => listener())
  }

  getState(): AuthState {
    return { ...this.state }
  }

  loadFromStorage() {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      this.state.token = token
      this.state.isAuthenticated = true
      // User will be loaded async via fetchCurrentUser
    }
  }

  async fetchCurrentUser(): Promise<User | null> {
    if (!this.state.token) {
      return null
    }

    try {
      const response = await api.get('/v1/auth/me')
      this.state.user = response.data
      this.state.isAuthenticated = true
      this.notify()
      return response.data
    } catch (error) {
      // Token invalid or expired
      this.logout()
      return null
    }
  }

  async login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.post('/v1/auth/login', { username, password })
      const { access_token } = response.data

      this.state.token = access_token
      this.state.isAuthenticated = true
      localStorage.setItem(TOKEN_KEY, access_token)

      // Fetch user info
      await this.fetchCurrentUser()

      this.notify()
      return { success: true }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      return { success: false, error: errorMessage }
    }
  }

  logout() {
    this.state.token = null
    this.state.user = null
    this.state.isAuthenticated = false
    localStorage.removeItem(TOKEN_KEY)
    this.notify()
    window.location.href = '/login'
  }

  hasRole(role: string): boolean {
    return this.state.user?.role === role
  }

  hasAnyRole(roles: string[]): boolean {
    return roles.some(role => this.state.user?.role === role)
  }
}

export const authStore = new AuthStore()

// React hook for auth state
export function useAuthStore() {
  const [, forceUpdate] = React.useReducer(x => x + 1, 0)

  React.useEffect(() => {
    return authStore.subscribe(forceUpdate)
  }, [])

  return authStore.getState()
}

// For non-React usage
export function getAuthToken(): string | null {
  return authStore.getState().token
}

export function getAuthUser(): User | null {
  return authStore.getState().user
}

// Import React for the hook
import * as React from 'react'
