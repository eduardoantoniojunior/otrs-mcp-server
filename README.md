# OTRS MCP Server

A [Model Context Protocol][mcp] (MCP) server for OTRS (Open Ticket Request System) API integration.

This provides access to OTRS ticket management through standardized MCP interfaces, allowing AI assistants to create, search, and manage tickets.

[mcp]: https://modelcontextprotocol.io/introduction/introduction

## Features

- [x] Create, read, update, and search tickets
- [x] Access ticket history and detailed information
- [x] Configurable default values for tickets
- [x] Docker containerization support
- [x] SSL/TLS support with certificate verification options
- [x] Provide interactive tools for AI assistants
- [x] MCP activity monitoring (tracks tool calls, success/error rates, duration)
- [x] REST API for frontend integration
- [x] React dashboard with real-time activity metrics

The list of tools is configurable, so you can choose which tools you want to make available to the MCP client.

## Prerequisites

### OTRS Server Configuration

Before using this MCP server, you need to configure your OTRS instance:

#### Step 1: Access OTRS Admin Panel

- URL: `https://your-otrs-server/otrs/index.pl?Action=Admin`
- Login with your admin credentials

#### Step 2: Configure Web Services

1. Navigate to: **System Administration → Web Services**
2. Create or verify you have a webservice (e.g., "TestInterface") with these operations:
   - ✅ SessionCreate
   - ✅ TicketCreate
   - ✅ TicketGet
   - ✅ TicketSearch
   - ✅ TicketUpdate
   - ✅ TicketHistoryGet

#### Step 3: Note Your Webservice URL

Your webservice URL should look like:

`https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/YourWebserviceName`

#### Step 4: Ensure User Permissions

Make sure your OTRS user has appropriate permissions for:

- Creating and updating tickets
- Accessing configuration items
- Using the Generic Interface

## Usage

### Docker (Recommended)

The easiest way to run otrs-mcp with [Claude Desktop](https://claude.ai/desktop) is using Docker. If you don't have Docker installed, you can get it from [Docker's official website](https://www.docker.com/get-started/).

#### Using Pre-built Image

You can use the pre-built Docker image from GitHub Container Registry:

```json
{
  "mcpServers": {
    "otrs": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "OTRS_BASE_URL=https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface",
        "-e",
        "OTRS_USERNAME=your-username",
        "-e",
        "OTRS_PASSWORD=your-password",
        "-e",
        "OTRS_VERIFY_SSL=false",
        "-e",
        "OTRS_DEFAULT_QUEUE=Raw",
        "-e",
        "OTRS_DEFAULT_STATE=new",
        "-e",
        "OTRS_DEFAULT_PRIORITY=3 normal",
        "ghcr.io/eduardoantoniojunior/otrs-mcp-server:latest"
      ]
    }
  }
}
```

#### Building Locally

If you prefer to build the image locally:

```bash
# Clone the repository
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server

# Build the Docker image
docker build -t otrs-mcp-server .

# Run the container
docker run --rm -i \
  -e OTRS_BASE_URL="https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface" \
  -e OTRS_USERNAME="your-username" \
  -e OTRS_PASSWORD="your-password" \
  -e OTRS_VERIFY_SSL="false" \
  otrs-mcp-server
```

### Running with UV

Alternatively, you can run the server directly using UV. First, set your environment variables:

```bash
export OTRS_BASE_URL="https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="your-username"
export OTRS_PASSWORD="your-password"
export OTRS_VERIFY_SSL="false"
export OTRS_DEFAULT_QUEUE="Raw"
export OTRS_DEFAULT_STATE="new"
export OTRS_DEFAULT_PRIORITY="3 normal"
export OTRS_DEFAULT_TYPE="Unclassified"
```

Then edit your Claude Desktop config file and add the server configuration:

```json
{
  "mcpServers": {
    "otrs": {
      "command": "uv",
      "args": [
        "--directory",
        "<full path to otrs-mcp-server directory>",
        "run",
        "src/otrs_mcp/main.py"
      ],
      "env": {
        "OTRS_BASE_URL": "https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface",
        "OTRS_USERNAME": "your-username",
        "OTRS_PASSWORD": "your-password",
        "OTRS_VERIFY_SSL": "false"
      }
    }
  }
}
```

> Note: if you see `Error: spawn uv ENOENT` in [Claude Desktop](https://claude.ai/desktop), you may need to specify the full path to `uv` or set the environment variable `NO_UV=1` in the configuration.

## Environment Variables

| Variable                | Required | Default                            | Description                         |
| ----------------------- | -------- | ---------------------------------- | ----------------------------------- |
| `OTRS_BASE_URL`         | ✅       | -                                  | Base URL for OTRS webservice        |
| `OTRS_USERNAME`         | ✅       | -                                  | OTRS username                       |
| `OTRS_PASSWORD`         | ✅       | -                                  | OTRS password                       |
| `OTRS_VERIFY_SSL`       | ❌       | `false`                            | Enable SSL certificate verification |
| `OTRS_TIMEOUT`          | ❌       | `30`                               | HTTP timeout in seconds             |
| `OTRS_DEBUG`            | ❌       | `false`                            | Enable debug logging                |
| `OTRS_DEFAULT_QUEUE`    | ❌       | `Raw`                              | Default queue for new tickets       |
| `OTRS_DEFAULT_STATE`    | ❌       | `new`                              | Default state for new tickets       |
| `OTRS_DEFAULT_PRIORITY` | ❌       | `3 normal`                         | Default priority for new tickets    |
| `OTRS_DEFAULT_TYPE`     | ❌       | `Unclassified`                     | Default type for new tickets        |
| `OTRS_CORS_ORIGINS`     | ❌       | `http://localhost:5173,http://localhost:8080` | Allowed CORS origins for API |

## Development

Contributions are welcome! Please open an issue or submit a pull request if you have any suggestions or improvements.

This project targets **Python 3.12** (see `requires-python` in `pyproject.toml`) and is validated for production use on that version.

This project uses [`uv`](https://github.com/astral-sh/uv) to manage dependencies. Install `uv` following the instructions for your platform:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Python 3.12 (if you don't have it) and create the virtual environment with the pinned dependencies:

```bash
# Install the interpreter (managed by uv)
uv python install 3.12

# Create the environment and install dependencies from uv.lock
uv sync --python 3.12 --extra dev
```

Alternatively, using the classic workflow:

```bash
uv venv --python 3.12
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
uv pip install -e .
```

### Testing

Run the unit tests:

```bash
# Install development dependencies
uv sync --extra dev

# Run unit tests
uv run pytest tests/unit/ -v

# Run with coverage report
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing
```

For integration testing against a real OTRS instance:

```bash
# Set environment variables
export OTRS_BASE_URL="https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="your-username"
export OTRS_PASSWORD="your-password"

# Run integration tests
uv run pytest tests/integration/ -v -m integration
```

### Publishing Docker Image

To publish the Docker image:

```bash
# Build the image
docker build -t otrs-mcp-server .

# Tag for your registry
docker tag otrs-mcp-server yourusername/otrs-mcp-server:latest

# Push
docker push yourusername/otrs-mcp-server:latest
```

## Available Tools

### 🎫 Ticket Management

- `create_ticket` - Create a new ticket in OTRS
- `get_ticket` - Get detailed information about a specific ticket
- `search_tickets` - Search for tickets based on various criteria
- `update_ticket` - Update an existing ticket's properties
- `get_ticket_history` - Get the complete history of a ticket

### 📊 Resources

- `otrs://ticket/{ticket_id}` - Direct access to ticket data
- `otrs://ticket/{ticket_id}/history` - Access to ticket history
- `otrs://search/tickets` - Overview of recent tickets

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**: Set `OTRS_VERIFY_SSL=false` for self-signed certificates
2. **HTTP 301 Redirects**: Ensure you're using HTTPS URLs if your OTRS server redirects HTTP to HTTPS
3. **Authentication Failures**: Verify your username, password, and webservice configuration
4. **Missing Operations**: Check that your OTRS webservice includes all required operations

### Debug Mode

Run the debug script to diagnose connection issues:

```bash
uv run python tests/debug_test.py
```

This will test both HTTP and HTTPS connections and provide detailed error information.

### Example Working Configuration

For reference, here's a working configuration example:

```bash
# Environment variables
export OTRS_BASE_URL="https://your-otrs-server/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="your-username"
export OTRS_PASSWORD="your-password"
export OTRS_VERIFY_SSL="false"
export OTRS_DEFAULT_QUEUE="Raw"
export OTRS_DEFAULT_STATE="new"
export OTRS_DEFAULT_PRIORITY="3 normal"
export OTRS_DEFAULT_TYPE="Unclassified"
```

### OTRS Webservice Operations

Your OTRS webservice should include these operations:

| Operation Name   | Controller                   | Description                    |
| ---------------- | ---------------------------- | ------------------------------ |
| TicketCreate     | Ticket::TicketCreate         | Create new tickets             |
| TicketGet        | Ticket::TicketGet            | Retrieve ticket details        |
| TicketSearch     | Ticket::TicketSearch         | Search for tickets             |
| TicketUpdate     | Ticket::TicketUpdate         | Update existing tickets        |
| TicketHistoryGet | Ticket::TicketHistoryGet     | Get ticket history             |

## License

Apache-2.0

---

[mcp]: https://modelcontextprotocol.io
