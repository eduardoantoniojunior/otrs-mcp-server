import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Copy, Check, Ban, Key, Filter, AlertTriangle, Clock, Search } from 'lucide-react';
import { api } from '../services/api';

interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  agent_name: string;
  permissions: string[];
  rate_limit: number;
  active: boolean;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  expires_at: string | null;
}

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('pt-BR');
}

function isExpiringSoon(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  const expires = new Date(expiresAt);
  const now = new Date();
  const diffDays = (expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays > 0 && diffDays <= 7;
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  return new Date(expiresAt) < new Date();
}

function daysUntilExpiry(expiresAt: string | null): number | null {
  if (!expiresAt) return null;
  const expires = new Date(expiresAt);
  const now = new Date();
  return Math.ceil((expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
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
    rate_limit: 100,
    expires_in_days: '' as string,
  });

  // Filters state
  const [filters, setFilters] = useState({
    search: '',
    permission: '' as '' | 'read' | 'write',
    status: '' as '' | 'active' | 'revoked' | 'expired' | 'expiring',
  });

  // Confirmation modal state
  const [confirmAction, setConfirmAction] = useState<{
    type: 'revoke' | 'delete';
    key: ApiKey;
  } | null>(null);

  const { data: keys, isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: () => api.listApiKeys(true),
  });

  // Filtered keys
  const filteredKeys = useMemo(() => {
    if (!keys) return [];
    
    return keys.filter(key => {
      // Search filter
      if (filters.search) {
        const search = filters.search.toLowerCase();
        const matchesSearch = 
          key.name.toLowerCase().includes(search) ||
          key.agent_name.toLowerCase().includes(search) ||
          key.key_prefix.toLowerCase().includes(search);
        if (!matchesSearch) return false;
      }

      // Permission filter
      if (filters.permission) {
        if (!key.permissions.includes(filters.permission)) return false;
      }

      // Status filter
      if (filters.status) {
        const expired = isExpired(key.expires_at);
        const expiring = isExpiringSoon(key.expires_at);
        
        switch (filters.status) {
          case 'active':
            if (!key.active || expired) return false;
            break;
          case 'revoked':
            if (key.active) return false;
            break;
          case 'expired':
            if (!expired) return false;
            break;
          case 'expiring':
            if (!expiring || expired) return false;
            break;
        }
      }

      return true;
    });
  }, [keys, filters]);

  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      api.createApiKey({
        name: data.name,
        agent_name: data.agent_name,
        permissions: data.permissions,
        rate_limit: data.rate_limit,
        expires_in_days: data.expires_in_days ? Number(data.expires_in_days) : undefined,
      }),
    onSuccess: (data) => {
      setNewKey(data.key);
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => api.revokeApiKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setConfirmAction(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteApiKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setConfirmAction(null);
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  const copyKey = () => {
    if (!newKey) return;

    const tryClipboard = async () => {
      // Preferred: async Clipboard API (requires HTTPS or localhost)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(newKey);
        return;
      }

      // Fallback: execCommand (works on HTTP)
      const textarea = document.createElement('textarea');
      textarea.value = newKey;
      textarea.style.position = 'fixed';
      textarea.style.top = '-9999px';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    };

    tryClipboard()
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        // Last resort: show the key in a prompt so the user can copy manually
        window.prompt('Copy the token manually (Ctrl+C):', newKey);
      });
  };

  const resetForm = () => {
    setForm({ name: '', agent_name: '', permissions: ['read'], rate_limit: 100, expires_in_days: '' });
    setShowCreate(false);
    setNewKey(null);
  };

  // Stats for filter badges
  const stats = useMemo(() => {
    if (!keys) return { active: 0, revoked: 0, expired: 0, expiring: 0 };
    return {
      active: keys.filter(k => k.active && !isExpired(k.expires_at)).length,
      revoked: keys.filter(k => !k.active).length,
      expired: keys.filter(k => isExpired(k.expires_at)).length,
      expiring: keys.filter(k => isExpiringSoon(k.expires_at) && !isExpired(k.expires_at)).length,
    };
  }, [keys]);

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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  Rate Limit (req/min)
                </label>
                <input
                  type="number"
                  value={form.rate_limit}
                  onChange={(e) => setForm({ ...form, rate_limit: Number(e.target.value) })}
                  className="input-dark"
                  placeholder="100"
                  min="0"
                  max="10000"
                />
                <p className="text-xs text-gray-500 mt-1">0 = unlimited</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Expires in (days)
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

      {/* Filters */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={14} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-300">Filters</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="input-dark text-sm pl-9"
              placeholder="Search name, agent..."
            />
          </div>
          <select
            value={filters.permission}
            onChange={(e) => setFilters({ ...filters, permission: e.target.value as '' | 'read' | 'write' })}
            className="input-dark text-sm"
          >
            <option value="">All permissions</option>
            <option value="read">Read only</option>
            <option value="write">Write access</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value as '' | 'active' | 'revoked' | 'expired' | 'expiring' })}
            className="input-dark text-sm"
          >
            <option value="">All statuses ({keys?.length || 0})</option>
            <option value="active">Active ({stats.active})</option>
            <option value="revoked">Revoked ({stats.revoked})</option>
            <option value="expired">Expired ({stats.expired})</option>
            <option value="expiring">Expiring soon ({stats.expiring})</option>
          </select>
          <button
            onClick={() => setFilters({ search: '', permission: '', status: '' })}
            className="btn-secondary text-sm"
          >
            Clear filters
          </button>
        </div>
      </div>

      {/* Tokens Table */}
      <div className="glass-card overflow-hidden">
        <table className="table-dark">
          <thead>
            <tr>
              <th>Name</th>
              <th>Agent</th>
              <th>Prefix</th>
              <th>Permissions</th>
              <th>Rate Limit</th>
              <th>Usage</th>
              <th>Last Used</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-gray-500">Loading...</td>
              </tr>
            ) : filteredKeys.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-gray-500">
                  {keys?.length === 0 
                    ? 'No MCP tokens found. Create one to get started.'
                    : 'No tokens match the current filters.'}
                </td>
              </tr>
            ) : (
              filteredKeys.map((key) => {
                const expired = isExpired(key.expires_at);
                const expiring = isExpiringSoon(key.expires_at);
                const neverUsed = key.usage_count === 0;
                const daysLeft = daysUntilExpiry(key.expires_at);

                return (
                  <tr key={key.id} className={expired ? 'opacity-60' : ''}>
                    <td>
                      <div className="flex items-center gap-2">
                        <Key size={14} className="text-amber-400 flex-shrink-0" />
                        <span className="font-medium text-gray-200">{key.name}</span>
                        {expiring && !expired && (
                          <span className="badge-amber text-[10px] flex items-center gap-1">
                            <AlertTriangle size={10} />
                            {daysLeft}d left
                          </span>
                        )}
                        {expired && (
                          <span className="badge-rose text-[10px]">Expired</span>
                        )}
                        {neverUsed && key.active && !expired && (
                          <span className="badge-gray text-[10px]">Never used</span>
                        )}
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
                    <td className="text-sm font-mono text-gray-400">
                      {key.rate_limit === 0 ? (
                        <span className="text-emerald-400">unlimited</span>
                      ) : (
                        `${key.rate_limit}/min`
                      )}
                    </td>
                    <td className="text-sm font-mono">{key.usage_count}</td>
                    <td className="text-sm text-gray-400">
                      <div className="flex items-center gap-1">
                        <Clock size={12} className="text-gray-500" />
                        {formatRelativeTime(key.last_used_at)}
                      </div>
                    </td>
                    <td>
                      <span className={key.active && !expired ? 'badge-green' : 'badge-rose'}>
                        {expired ? 'Expired' : key.active ? 'Active' : 'Revoked'}
                      </span>
                    </td>
                    <td className="text-right">
                      <div className="flex gap-2 justify-end">
                        {key.active && !expired && (
                          <button
                            onClick={() => setConfirmAction({ type: 'revoke', key })}
                            className="text-amber-400/70 hover:text-amber-400 transition-colors p-1"
                            title="Revoke"
                          >
                            <Ban size={15} />
                          </button>
                        )}
                        <button
                          onClick={() => setConfirmAction({ type: 'delete', key })}
                          className="text-rose-400/70 hover:text-rose-400 transition-colors p-1"
                          title="Delete"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Confirmation Modal */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 animate-fade-in">
          <div className="glass-card p-6 max-w-md w-full mx-4 animate-slide-up">
            <h3 className="text-lg font-bold text-white mb-2">
              {confirmAction.type === 'revoke' ? 'Revoke Token' : 'Delete Token'}
            </h3>
            <div className="space-y-3 mb-5">
              <p className="text-gray-400 text-sm">
                {confirmAction.type === 'revoke' 
                  ? 'This will immediately disable the token. The agent will no longer be able to authenticate.'
                  : 'This will permanently delete the token. This action cannot be undone.'}
              </p>
              <div className="bg-navy-900/50 rounded-lg p-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Name:</span>
                  <span className="text-gray-200">{confirmAction.key.name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Agent:</span>
                  <span className="text-gray-200">{confirmAction.key.agent_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total requests:</span>
                  <span className="text-gray-200">{confirmAction.key.usage_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Created:</span>
                  <span className="text-gray-200">
                    {new Date(confirmAction.key.created_at).toLocaleDateString('pt-BR')}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  if (confirmAction.type === 'revoke') {
                    revokeMutation.mutate(confirmAction.key.id);
                  } else {
                    deleteMutation.mutate(confirmAction.key.id);
                  }
                }}
                disabled={revokeMutation.isPending || deleteMutation.isPending}
                className={confirmAction.type === 'revoke' ? 'btn-amber flex-1' : 'btn-danger flex-1'}
              >
                {revokeMutation.isPending || deleteMutation.isPending 
                  ? 'Processing...' 
                  : confirmAction.type === 'revoke' ? 'Revoke Token' : 'Delete Token'}
              </button>
              <button
                onClick={() => setConfirmAction(null)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
