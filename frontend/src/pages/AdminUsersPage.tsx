import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, UserPlus, Shield } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface AdminUser {
  id: number;
  username: string;
  active: boolean;
  created_at: string;
}

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');

  const { data: users, isLoading } = useQuery<AdminUser[]>({
    queryKey: ['admin-users'],
    queryFn: () => api.listUsers(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { username: string; password: string }) => api.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setShowCreate(false);
      setForm({ username: '', password: '' });
      setError('');
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    createMutation.mutate(form);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Users</h1>
          <p className="section-subtitle">Manage administrator accounts</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary" id="create-user-btn">
          <UserPlus size={16} />
          New User
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="glass-card p-6 animate-slide-up">
          <h2 className="section-title mb-5">New Admin User</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="input-dark"
                  placeholder="e.g. joao.silva"
                  required
                  minLength={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="input-dark"
                  placeholder="Min. 6 characters"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {error && (
              <div className="bg-accent-rose/10 border border-accent-rose/20 text-rose-400 px-4 py-2.5 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                {createMutation.isPending ? 'Creating...' : 'Create User'}
              </button>
              <button
                type="button"
                onClick={() => { setShowCreate(false); setError(''); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="glass-card overflow-hidden">
        <table className="table-dark">
          <thead>
            <tr>
              <th>User</th>
              <th>Status</th>
              <th>Created</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} className="text-center py-8 text-gray-500">Loading...</td>
              </tr>
            ) : users?.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center py-8 text-gray-500">No admin users found</td>
              </tr>
            ) : (
              users?.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent-blue/15 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-accent-blue">
                          {u.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-200">{u.username}</span>
                        {currentUser?.username === u.username && (
                          <span className="badge-blue ml-2">you</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={u.active ? 'badge-green' : 'badge-rose'}>
                      {u.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="text-sm text-gray-400">
                    {new Date(u.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="text-right">
                    {currentUser?.username !== u.username ? (
                      <button
                        onClick={() => {
                          if (confirm(`Delete user "${u.username}"?`)) {
                            deleteMutation.mutate(u.id);
                          }
                        }}
                        className="text-rose-400/70 hover:text-rose-400 transition-colors p-1"
                        title="Delete user"
                      >
                        <Trash2 size={15} />
                      </button>
                    ) : (
                      <span className="text-xs text-gray-600">
                        <Shield size={14} className="inline" /> Protected
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
