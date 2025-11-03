import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Users() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const queryClient = useQueryClient()

  // Fetch all users
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/v1/users'),
    refetchInterval: 30000
  })

  // Create user mutation
  const createMutation = useMutation({
    mutationFn: (userData: any) => api.post('/v1/users', userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowCreateModal(false)
      alert('User created successfully')
    },
    onError: (error: any) => {
      alert(`Failed to create user: ${error.response?.data?.detail || error.message}`)
    }
  })

  // Toggle enabled mutation
  const toggleMutation = useMutation({
    mutationFn: ({ userId, enabled }: { userId: number; enabled: boolean }) =>
      api.patch(`/v1/users/${userId}`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      alert('User status updated successfully')
    },
    onError: (error: any) => {
      alert(`Failed to update user: ${error.response?.data?.detail || error.message}`)
    }
  })

  // Delete user mutation
  const deleteMutation = useMutation({
    mutationFn: (userId: number) => api.delete(`/v1/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      alert('User deleted successfully')
    },
    onError: (error: any) => {
      alert(`Failed to delete user: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleCreateUser = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)

    const userData = {
      username: formData.get('username'),
      email: formData.get('email'),
      password: formData.get('password'),
      role: formData.get('role'),
      tenant_id: formData.get('tenant_id') || undefined,
      enabled: true
    }

    createMutation.mutate(userData)
  }

  const handleToggleEnabled = (userId: number, currentEnabled: boolean) => {
    if (confirm(`Are you sure you want to ${currentEnabled ? 'disable' : 'enable'} this user?`)) {
      toggleMutation.mutate({ userId, enabled: !currentEnabled })
    }
  }

  const handleDeleteUser = (userId: number, username: string) => {
    if (confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
      deleteMutation.mutate(userId)
    }
  }

  // IMPORTANT: Filter out platform_admin users (RBAC guard)
  const filteredUsers = users?.data?.filter((user: any) => user.role !== 'platform_admin') || []

  const roleColor = (role: string) => {
    switch (role) {
      case 'tenant_admin':
        return '#007bff'
      case 'tenant_reporter':
        return '#28a745'
      default:
        return '#6c757d'
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>User Management</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          style={{
            padding: '10px 20px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          + Create User
        </button>
      </div>

      <div className="card">
        <h3>
          Users ({filteredUsers.length})
          {isLoading && <span style={{ marginLeft: '10px', color: '#999' }}>Loading...</span>}
        </h3>

        <div style={{ overflowX: 'auto', marginTop: '15px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Username</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Email</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Role</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Tenant ID</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Created</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user: any) => (
                <tr key={user.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>{user.username}</td>
                  <td style={{ padding: '12px' }}>{user.email}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: roleColor(user.role),
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {user.role}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>{user.tenant_id || '-'}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: user.enabled ? '#28a745' : '#dc3545',
                      color: 'white',
                      fontSize: '11px'
                    }}>
                      {user.enabled ? 'ENABLED' : 'DISABLED'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontSize: '13px', color: '#666' }}>
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <button
                      onClick={() => handleToggleEnabled(user.id, user.enabled)}
                      style={{
                        padding: '6px 12px',
                        marginRight: '8px',
                        backgroundColor: user.enabled ? '#ffc107' : '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px'
                      }}
                    >
                      {user.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleDeleteUser(user.id, user.username)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px'
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredUsers.length === 0 && !isLoading && (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
              No users found
            </div>
          )}
        </div>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{
            width: '500px',
            maxWidth: '90%',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <h3>Create New User</h3>
            <form onSubmit={handleCreateUser}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Username *
                </label>
                <input
                  type="text"
                  name="username"
                  required
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                />
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Email *
                </label>
                <input
                  type="email"
                  name="email"
                  required
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                />
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Password *
                </label>
                <input
                  type="password"
                  name="password"
                  required
                  minLength={8}
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                />
                <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  Minimum 8 characters
                </p>
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Role *
                </label>
                <select
                  name="role"
                  required
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                >
                  <option value="">Select role...</option>
                  <option value="tenant_admin">Tenant Admin</option>
                  <option value="tenant_reporter">Tenant Reporter</option>
                </select>
                <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  Note: Platform admin role is restricted and cannot be created here
                </p>
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Tenant ID (optional)
                </label>
                <input
                  type="text"
                  name="tenant_id"
                  placeholder="Leave empty for multi-tenant access"
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                />
                <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  Specify tenant ID to restrict user to a specific tenant
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '10px 20px',
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
                  disabled={createMutation.isPending}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: createMutation.isPending ? 'not-allowed' : 'pointer'
                  }}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
