# MCP Best Practices Guide

Comprehensive best practices for building Model Context Protocol (MCP) servers. Follow these conventions to ensure consistency, security, and maintainability across MCP implementations.

---

## Server Naming

Use clear, descriptive names that identify the service being wrapped.

### Python Servers
- Pattern: `{service}_mcp`
- Examples: `otrs_mcp`, `jira_mcp`, `github_mcp`
- Use snake_case following Python conventions

### Node/TypeScript Servers
- Pattern: `{service}-mcp-server`
- Examples: `otrs-mcp-server`, `jira-mcp-server`, `github-mcp-server`
- Use kebab-case following Node conventions

### General Rules
- Keep names lowercase
- The service name should match the external API or system being integrated
- Avoid generic names like `my-server` or `api-mcp`

---

## Tool Naming and Design

### Naming Conventions
- Use `snake_case` for all tool names
- Prefix tools with the service name to avoid collisions: `otrs_get_ticket`, `otrs_create_ticket`
- Use verb-first naming: `get_`, `list_`, `create_`, `update_`, `delete_`, `search_`
- Keep names concise but descriptive

### Design Principles
- **Single responsibility**: Each tool should do one thing well
- **Minimal required parameters**: Only require what is strictly necessary; use sensible defaults for the rest
- **Consistent parameter naming**: Use the same parameter names across tools for the same concept (e.g., always `ticket_id`, not sometimes `id` and sometimes `ticket_id`)
- **Predictable behavior**: Tools with similar names should behave similarly
- **Composability**: Design tools so they can be chained together by the LLM

### Parameter Guidelines
- Use descriptive parameter names, not abbreviations
- Provide clear descriptions for every parameter
- Mark parameters as required only when truly necessary
- Include default values where appropriate
- Use enums to constrain values when a fixed set of options exists

---

## Response Formats

### JSON Responses
Use JSON for structured data that the LLM needs to process or reference:

```json
{
  "ticket_id": "2024010100001",
  "title": "Server outage in production",
  "state": "open",
  "priority": "high",
  "created": "2024-01-01T10:00:00Z"
}
```

### Markdown Responses
Use Markdown for human-readable summaries and reports:

```markdown
## Ticket #2024010100001
**Title:** Server outage in production
**State:** Open | **Priority:** High
**Created:** 2024-01-01 10:00 UTC
```

### Guidelines
- Return JSON when the data will be further processed or referenced by subsequent tool calls
- Return Markdown when the data is primarily for display to the user
- Include both formats when appropriate (structured data with a summary)
- Keep responses concise; avoid returning unnecessary fields
- Use consistent date formats (ISO 8601)
- Avoid deeply nested structures when a flatter format conveys the same information

---

## Pagination

For tools that return lists, implement consistent pagination using the following pattern:

### Request Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 25 | Maximum number of items to return (max: 100) |
| `offset` | integer | 0 | Number of items to skip |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `items` | array | The list of results |
| `has_more` | boolean | Whether more results are available |
| `next_offset` | integer or null | Offset to use for the next page, null if no more results |
| `total_count` | integer | Total number of matching items (if available from the API) |

### Example Response

```json
{
  "items": [
    { "ticket_id": "001", "title": "First ticket" },
    { "ticket_id": "002", "title": "Second ticket" }
  ],
  "has_more": true,
  "next_offset": 25,
  "total_count": 142
}
```

### Guidelines
- Always default to a reasonable page size (25 is a good starting point)
- Cap the maximum page size to prevent excessive responses (100 is a reasonable cap)
- Return `total_count` when the upstream API provides it without extra cost
- Set `next_offset` to null when there are no more results
- The LLM can use `has_more` to decide whether to fetch additional pages

---

## Transport Options

### Streamable HTTP (Remote Servers)
- Recommended for remote/deployed MCP servers
- Supports multiple concurrent clients
- Works behind load balancers and reverse proxies
- Use when the server needs to be accessed over a network
- Endpoint convention: `POST /mcp`

### stdio (Local Servers)
- Recommended for local development and local-only integrations
- Simple to set up and debug
- One client per server process
- Use when the server runs on the same machine as the client
- Good for CLI tools and IDE integrations

### Selection Guidelines
- Default to **stdio** for development and single-user setups
- Use **Streamable HTTP** for shared or production deployments
- Consider your deployment model early; it affects configuration and testing
- Both transports use the same MCP protocol messages

---

## Security Best Practices

### Authentication
- Use **OAuth 2.1** for production deployments with user-facing authentication
- Support **API keys** for service-to-service communication
- Never hardcode credentials in source code

### Credential Management
- Store API keys and secrets in environment variables
- Use `.env` files for local development (add `.env` to `.gitignore`)
- Document all required environment variables in the README
- Provide a `.env.example` file with placeholder values

```bash
# .env.example
OTRS_BASE_URL=https://otrs.example.com
OTRS_API_USER=api_user
OTRS_API_PASSWORD=changeme
```

### Input Validation
- Validate all input parameters before making API calls
- Sanitize strings to prevent injection attacks
- Enforce type constraints (numbers, dates, enums)
- Set reasonable limits on string lengths and array sizes
- Return clear error messages for invalid input

### Network Security
- Use HTTPS for all external API calls
- Validate SSL certificates (do not disable verification)
- Implement request timeouts to prevent hanging connections
- Rate-limit outgoing requests to avoid overwhelming upstream APIs

### Data Handling
- Never log sensitive data (passwords, tokens, personal information)
- Minimize the data returned to what the LLM actually needs
- Be cautious with data that could contain PII

---

## Tool Annotations

Use tool annotations to help clients understand the behavior and impact of each tool. These hints enable clients to make informed decisions about tool execution.

### Available Annotations

| Annotation | Type | Default | Description |
|-----------|------|---------|-------------|
| `readOnlyHint` | boolean | false | Tool does not modify any state; safe to run without confirmation |
| `destructiveHint` | boolean | true | Tool may perform destructive or irreversible operations |
| `idempotentHint` | boolean | false | Calling the tool multiple times with the same input has the same effect as calling it once |
| `openWorldHint` | boolean | true | Tool interacts with external systems beyond the server's control |

### Guidelines
- Mark read operations with `readOnlyHint: true` and `destructiveHint: false`
- Mark delete operations with `destructiveHint: true` and `idempotentHint: false`
- Mark update/PUT operations with `idempotentHint: true` when they are truly idempotent
- Set `openWorldHint: true` for tools that call external APIs
- Be accurate with annotations; they affect how clients handle tool execution and user confirmations

### Examples

```json
{
  "name": "otrs_get_ticket",
  "annotations": {
    "readOnlyHint": true,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": true
  }
}
```

```json
{
  "name": "otrs_delete_ticket",
  "annotations": {
    "readOnlyHint": false,
    "destructiveHint": true,
    "idempotentHint": false,
    "openWorldHint": true
  }
}
```

---

## Error Handling

### JSON-RPC Error Codes

Use standard JSON-RPC error codes for consistency:

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse error | Invalid JSON received |
| -32600 | Invalid request | The request is not a valid JSON-RPC request |
| -32601 | Method not found | The requested tool does not exist |
| -32602 | Invalid params | Invalid or missing parameters |
| -32603 | Internal error | Unexpected server-side error |

### Application Error Guidelines
- Return errors as `isError: true` in tool results for recoverable application errors
- Include a clear, actionable error message the LLM can use to adjust its approach
- Categorize errors: authentication, authorization, not found, validation, rate limit, upstream failure
- Do not expose internal stack traces or sensitive system information in error messages
- Log detailed errors server-side for debugging

### Error Response Example

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Ticket not found: No ticket exists with ID '999999'. Verify the ticket ID and try again."
    }
  ]
}
```

### Retry Guidance
- Implement retries with exponential backoff for transient upstream failures
- Set a maximum retry count (3 is a reasonable default)
- Do not retry on authentication or validation errors
- Include rate-limit headers in error responses when applicable

---

## Testing Requirements

### Unit Tests
- Test each tool handler in isolation with mocked API responses
- Cover success paths, error paths, and edge cases
- Validate parameter parsing and input validation logic
- Test pagination logic

### Integration Tests
- Test against a staging or sandbox environment when available
- Verify end-to-end flows (create, read, update, delete)
- Test authentication and authorization flows
- Test error scenarios with real API responses

### MCP Protocol Tests
- Verify tool discovery (`tools/list`) returns correct schemas
- Test tool invocation through the MCP protocol layer
- Validate response formats match the declared schemas
- Test with an MCP client (e.g., MCP Inspector)

### Test Organization
- Group tests by tool or feature
- Use fixtures for common test data
- Mock external API calls in unit tests
- Document how to run tests in the README

---

## Documentation Requirements

### README
Every MCP server must include a README with:
- Server description and purpose
- Prerequisites and system requirements
- Installation instructions
- Configuration (all environment variables with descriptions)
- Available tools with descriptions and example usage
- Transport setup (stdio and/or HTTP)
- How to run tests
- Troubleshooting common issues

### Tool Documentation
Each tool should document:
- Purpose and when to use it
- All parameters with types, descriptions, defaults, and constraints
- Response format with example
- Error cases and how to handle them
- Relationship to other tools (e.g., "Use `list_tickets` to find IDs for this tool")

### Inline Code Documentation
- Add docstrings or JSDoc to all tool handler functions
- Comment complex business logic
- Document any assumptions or limitations
- Include links to relevant API documentation for the upstream service
