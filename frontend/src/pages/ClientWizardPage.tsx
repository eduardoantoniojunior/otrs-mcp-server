import { useState } from 'react';
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';

const CLIENTS = [
  {
    id: 'claude-desktop',
    name: 'Claude Desktop',
    icon: '🤖',
    config: (url: string, key: string) => JSON.stringify({
      mcpServers: {
        "otrs-mcp": {
          url: `${url}/mcp`,
          headers: {
            Authorization: `Bearer ${key}`,
          },
        },
      },
    }, null, 2),
    instructions: [
      'Open Claude Desktop settings',
      'Go to "MCP Servers" section',
      'Click "Add Server"',
      'Paste the configuration below',
      'Restart Claude Desktop',
    ],
    configFile: 'claude_desktop_config.json',
  },
  {
    id: 'vscode',
    name: 'VS Code (Copilot / Continue)',
    icon: '💻',
    config: (url: string, key: string) => JSON.stringify({
      servers: {
        "otrs-mcp": {
          type: "http",
          url: `${url}/mcp`,
          headers: {
            Authorization: `Bearer ${key}`,
          },
        },
      },
    }, null, 2),
    instructions: [
      'Open VS Code settings (Ctrl+Shift+P → "Settings JSON")',
      'Add the MCP server configuration',
      'Or use the .vscode/mcp.json file in your project',
    ],
    configFile: '.vscode/mcp.json',
  },
  {
    id: 'curl',
    name: 'cURL (Testing)',
    icon: '⚡',
    config: (url: string, key: string) => `# Initialize
curl -X POST ${url}/mcp \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json, text/event-stream" \\
  -H "Authorization: Bearer ${key}" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }'`,
    instructions: [
      'Use these commands to test the MCP connection',
      'The initialize command should return server capabilities',
    ],
    configFile: 'Terminal',
  },
  {
    id: 'python',
    name: 'Python MCP SDK',
    icon: '🐍',
    config: (url: string, key: string) => `from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def main():
    headers = {"Authorization": "Bearer ${key}"}
    
    async with streamablehttp_client(
        "${url}/mcp", headers=headers
    ) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            
            # Call a tool
            result = await session.call_tool(
                "search_tickets",
                arguments={"queue": "Suporte::Zabbix", "limit": 5}
            )
            print(result)

import asyncio
asyncio.run(main())`,
    instructions: [
      'Install the MCP SDK: pip install mcp',
      'Use streamablehttp_client for Streamable HTTP transport',
      'The server exposes tools like search_tickets, get_ticket, etc.',
    ],
    configFile: 'script.py',
  },
];

export default function ClientWizardPage() {
  const [expanded, setExpanded] = useState<string>('claude-desktop');
  const [copied, setCopied] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState('http://your-server:8081');
  const [apiKey, setApiKey] = useState('sk-otrs-your-api-key');

  const copyConfig = (clientId: string, config: string) => {
    navigator.clipboard.writeText(config);
    setCopied(clientId);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Client MCP Wizard</h1>
        <p className="section-subtitle">Configure MCP clients to connect to this server</p>
      </div>

      {/* Connection Details */}
      <div className="glass-card p-5">
        <h2 className="section-title mb-4">Connection Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Server URL</label>
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              className="input-dark"
              placeholder="http://your-server:8081"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">API Key</label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="input-dark font-mono text-xs"
              placeholder="sk-otrs-..."
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          These values will be used in the configuration snippets below. Create a token in{' '}
          <a href="/mcp-tokens" className="text-accent-blue hover:underline">MCP Tokens</a> if you don't have one.
        </p>
      </div>

      {/* Client Configs */}
      <div className="space-y-3">
        {CLIENTS.map((client) => {
          const isOpen = expanded === client.id;
          const config = client.config(serverUrl, apiKey);

          return (
            <div key={client.id} className="glass-card overflow-hidden">
              {/* Header */}
              <button
                onClick={() => setExpanded(isOpen ? '' : client.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{client.icon}</span>
                  <span className="font-medium text-gray-200">{client.name}</span>
                </div>
                {isOpen ? (
                  <ChevronDown size={16} className="text-gray-400" />
                ) : (
                  <ChevronRight size={16} className="text-gray-400" />
                )}
              </button>

              {/* Content */}
              {isOpen && (
                <div className="px-4 pb-5 border-t border-white/[0.04] pt-4 animate-fade-in">
                  {/* Instructions */}
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">Setup Steps:</h3>
                    <ol className="space-y-1.5">
                      {client.instructions.map((step, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                          <span className="text-accent-blue font-mono text-xs mt-0.5">{i + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>

                  {/* Config */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500 font-mono">{client.configFile}</span>
                      <button
                        onClick={() => copyConfig(client.id, config)}
                        className="btn-secondary px-2.5 py-1.5 text-xs"
                      >
                        {copied === client.id ? (
                          <>
                            <Check size={12} className="text-emerald-400" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy size={12} />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="bg-navy-950 border border-white/[0.06] rounded-lg p-4 text-sm font-mono text-gray-300 overflow-x-auto">
                      {config}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
