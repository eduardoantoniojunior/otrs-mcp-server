import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Copy, Check, Ban, Key } from 'lucide-react';
import { api } from '../services/api';

interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  agent_name: string;
  permissions: string[];
  active: boolean;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  expires_at: string | null;
}

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({
    name: '',
    agent_name: '',
    permissions: ['read'],
    expires_in_days: '' as string,
  });

  const { data: keys, isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: () => api.listApiKeys(true),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      api.createApiKey({
        name: data.name,
        agent_name: data.agent_name,
        permissions: data.permissions,
        expires_in_days: data.expires_in_days ? Number(data.expires_in_days) : undefined,
      }),
    onSuccess: (data) => {
      setNewKey(data.key);
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => api.revokeApiKey(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteApiKey(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  const copyKey = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const resetForm = () => {
    setForm({ name: '', agent_name: '', permissions: ['read'], expires_in_days: '' });
    setShowCreate(false);
    setNewKey(null);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">MCP Tokens</h1>
          <p className="section-subtitle">Manage access tokens for MCP agents</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary" id="create-token-btn">
          <Plus size={16} />
          Create Token
        </button>
      </div>

      {/* New Key Created Banner */}
      {newKey && (
        <div className="glass-card p-5 border-accent-emerald/30 animate-slide-up">
          <div className="flex items-center gap-2 mb-2">
            <Check size={18} className="text-emerald-400" />
            <span className="font-medium text-emerald-400">Token created successfully!</span>
          </div>
          <p className="text-sm text-gray-400 mb-3">
            Save this token now. It won't be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-navy-900/80 px-4 py-2.5 rounded-lg text-sm font-mono text-gray-200 break-all border border-white/[0.06]">
              {newKey}
            </code>
            <button onClick={copyKey} className="btn-secondary px-3 py-2.5" title="Copy">
              {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
            </button>
          </div>
          <button onClick={resetForm} className="text-sm text-gray-500 hover:text-gray-300 mt-3 transition-colors">
            Close
          </button>
        </div>
      )}

      {/* Create Form */}
      {showCreate && !newKey && (
        <div className="glass-card p-6 animate-slide-up">
          <h2 className="section-title mb-5">New MCP Token</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="input-dark"
                  placeholder="e.g. Claude Desktop - Joao"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Agent Name</label>
                <input
                  type="text"
                  value={form.agent_name}
                  onChange={(e) => setForm({ ...form, agent_name: e.target.value })}
                  className="input-dark"
                  placeholder="e.g. claude-desktop-joao"
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Permissions</label>
                <div className="flex gap-4 mt-1">
                  {['read', 'write'].map((perm) => (
                    <label key={perm} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.permissions.includes(perm)}
                        onChange={(e) => {
                          const perms = e.target.checked
                            ? [...form.permissions, perm]
                            : form.permissions.filter((p) => p !== perm);
                          setForm({ ...form, permissions: perms });
                        }}
                        className="rounded border-white/20 bg-navy-900 text-accent-blue focus:ring-accent-blue/40"
                      />
                      <span className="text-sm text-gray-300">{perm}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Expires in (days, optional)
                </label>
                <input
                  type="number"
                  value={form.expires_in_days}
                  onChange={(e) => setForm({ ...form, expires_in_days: e.target.value })}
                  className="input-dark"
                  placeholder="Never"
                  min="1"
                  max="365"
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                {createMutation.isPending ? 'Creating...' : 'Create Token'}
              </button>
              <button type="button" onClick={resetForm} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tokens Table */}
      <div className="glass-card overflow-hidden">
        <table className="table-dark">
          <thead>
            <tr>
              <th>Name</th>
              <th>Agent</th>
              <th>Prefix</th>
              <th>Permissions</th>
              <th>Usage</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">Loading...</td>
              </tr>
            ) : keys?.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">
                  No MCP tokens found. Create one to get started.
                </td>
              </tr>
            ) : (
              keys?.map((key) => (
                <tr key={key.id}>
                  <td>
                    <div className="flex items-center gap-2">
                      <Key size={14} className="text-amber-400 flex-shrink-0" />
                      <span className="font-medium text-gray-200">{key.name}</span>
                    </div>
                  </td>
                  <td className="text-sm">{key.agent_name}</td>
                  <td>
                    <code className="text-xs bg-white/[0.04] px-2 py-1 rounded font-mono">{key.key_prefix}...</code>
                  </td>
                  <td>
                    <div className="flex gap-1">
                      {key.permissions.map((p) => (
                        <span key={p} className={p === 'write' ? 'badge-amber' : 'badge-blue'}>
                          {p}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="text-sm font-mono">{key.usage_count}</td>
                  <td>
                    <span className={key.active ? 'badge-green' : 'badge-rose'}>
                      {key.active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="text-right">
                    <div className="flex gap-2 justify-end">
                      {key.active && (
                        <button
                          onClick={() => revokeMutation.mutate(key.id)}
                          className="text-amber-400/70 hover:text-amber-400 transition-colors p-1"
                          title="Revoke"
                        >
                          <Ban size={15} />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (confirm('Permanently delete this token?')) {
                            deleteMutation.mutate(key.id);
                          }
                        }}
                        className="text-rose-400/70 hover:text-rose-400 transition-colors p-1"
                        title="Delete"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
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
