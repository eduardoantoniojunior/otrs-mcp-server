import { useHealth, useConfig } from '../hooks/useTickets';
import { Server, Database, Shield, Globe, CheckCircle, XCircle } from 'lucide-react';

export default function SettingsPage() {
  const { data: healthData, isLoading: healthLoading } = useHealth();
  const { data: configData, isLoading: configLoading } = useConfig();

  const isOnline = healthData?.status === 'ok';
  const queues = configData?.valid_queues ?? [];
  const types = configData?.valid_types ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="section-subtitle">Server configuration and connection status</p>
      </div>

      {/* Connection Status */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-5">
          <Server size={18} className="text-gray-400" />
          <h2 className="section-title">OTRS Connection</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-center gap-3">
            {healthLoading ? (
              <div className="w-10 h-10 rounded-lg bg-white/[0.04] animate-pulse" />
            ) : isOnline ? (
              <div className="w-10 h-10 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
                <CheckCircle size={20} className="text-emerald-400" />
              </div>
            ) : (
              <div className="w-10 h-10 rounded-lg bg-accent-rose/10 flex items-center justify-center">
                <XCircle size={20} className="text-rose-400" />
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-gray-200">API Status</p>
              <p className={`text-sm ${isOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                {healthLoading ? 'Checking...' : isOnline ? 'Connected' : 'Offline'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
              <Globe size={20} className="text-accent-blue" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-200">MCP Transport</p>
              <p className="text-sm text-gray-400">Streamable HTTP</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-violet/10 flex items-center justify-center">
              <Shield size={20} className="text-violet-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-200">Authentication</p>
              <p className="text-sm text-gray-400">Bearer Token (API Key)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Server Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Queues */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Database size={18} className="text-gray-400" />
            <h2 className="section-title">Valid Queues</h2>
          </div>
          {configLoading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : queues.length === 0 ? (
            <p className="text-sm text-gray-500">No queues configured (OTRS_VALID_QUEUES not set)</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {queues.map((q) => (
                <span key={q} className="badge-blue">{q}</span>
              ))}
            </div>
          )}
        </div>

        {/* Types */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Database size={18} className="text-gray-400" />
            <h2 className="section-title">Valid Types</h2>
          </div>
          {configLoading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : types.length === 0 ? (
            <p className="text-sm text-gray-500">No types configured (OTRS_VALID_TYPES not set)</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {types.map((t) => (
                <span key={t} className="badge-violet">{t}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Server Version */}
      <div className="glass-card p-6">
        <h2 className="section-title mb-4">Server Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-500 mb-1">Version</p>
            <p className="text-gray-200 font-mono">0.2.0</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">MCP Endpoint</p>
            <code className="text-accent-blue bg-white/[0.04] px-2 py-1 rounded text-xs">/mcp</code>
          </div>
          <div>
            <p className="text-gray-500 mb-1">API Endpoint</p>
            <code className="text-accent-blue bg-white/[0.04] px-2 py-1 rounded text-xs">/api</code>
          </div>
        </div>
      </div>
    </div>
  );
}
