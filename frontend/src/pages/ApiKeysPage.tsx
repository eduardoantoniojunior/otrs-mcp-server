import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Shield, Copy, Check } from 'lucide-react';
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-500">Gerencie as chaves de acesso para agentes</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={18} />
          Nova Key
        </button>
      </div>

      {newKey && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Check className="text-green-600" size={18} />
            <span className="font-medium text-green-800">API Key criada com sucesso!</span>
          </div>
          <p className="text-sm text-green-700 mb-3">
            Guarde esta chave. Ela nao sera mostrada novamente.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white px-3 py-2 rounded border text-sm font-mono break-all">
              {newKey}
            </code>
            <button onClick={copyKey} className="p-2 hover:bg-green-100 rounded transition-colors">
              {copied ? <Check className="text-green-600" size={18} /> : <Copy size={18} />}
            </button>
          </div>
          <button
            onClick={() => setNewKey(null)}
            className="mt-3 text-sm text-green-700 hover:text-green-900"
          >
            Fechar
          </button>
        </div>
      )}

      {showCreate && !newKey && (
        <div className="bg-white border rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Nova API Key</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Ex: Claude Desktop - Joao"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Agente</label>
                <input
                  type="text"
                  value={form.agent_name}
                  onChange={(e) => setForm({ ...form, agent_name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Ex: claude-desktop-joao"
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Permissoes</label>
                <div className="flex gap-4">
                  {['read', 'write'].map((perm) => (
                    <label key={perm} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.permissions.includes(perm)}
                        onChange={(e) => {
                          const perms = e.target.checked
                            ? [...form.permissions, perm]
                            : form.permissions.filter((p) => p !== perm);
                          setForm({ ...form, permissions: perms });
                        }}
                        className="rounded"
                      />
                      <span className="text-sm">{perm}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expirar em (dias, opcional)
                </label>
                <input
                  type="number"
                  value={form.expires_in_days}
                  onChange={(e) => setForm({ ...form, expires_in_days: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Nunca"
                  min="1"
                  max="365"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Criando...' : 'Criar Key'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Nome</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Agente</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Prefixo</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Permissoes</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Usos</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Status</th>
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600">Acoes</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  Carregando...
                </td>
              </tr>
            ) : keys?.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  Nenhuma API key encontrada
                </td>
              </tr>
            ) : (
              keys?.map((key) => (
                <tr key={key.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Shield size={16} className="text-gray-400" />
                      <span className="font-medium">{key.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{key.agent_name}</td>
                  <td className="px-4 py-3">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">{key.key_prefix}...</code>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {key.permissions.map((p) => (
                        <span
                          key={p}
                          className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{key.usage_count}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        key.active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {key.active ? 'Ativa' : 'Revogada'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      {key.active && (
                        <button
                          onClick={() => revokeMutation.mutate(key.id)}
                          className="text-yellow-600 hover:text-yellow-700 text-sm"
                          title="Revogar"
                        >
                          Revogar
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (confirm('Remover permanentemente esta key?')) {
                            deleteMutation.mutate(key.id);
                          }
                        }}
                        className="text-red-600 hover:text-red-700"
                        title="Remover"
                      >
                        <Trash2 size={16} />
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
