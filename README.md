# TraderFit Bridge (StdIO)

This package provides a Machine Cognition Protocol (MCP) bridge using standard input/output (stdio) to connect an MCP client (like Cursor) to the TraderFitAI backend API.

## Features

*   Dynamically fetches available tools from the TraderFitAI OpenAPI schema.
*   Executes tool calls by forwarding requests to the TraderFitAI API.
*   Authenticates with the backend using an API key provided via environment variable.

## Installation

```bash
# Install from PyPI
pip install traderfit-bridge
```

## Configuration

This bridge uses the command-based configuration method for MCP clients like Cursor. The package includes a helper script to generate the necessary JSON snippet for you.

1.  **Install the package:**
    ```bash
    pip install traderfit-bridge
    ```
2.  **Generate your API Key:** Obtain your API key from the TraderFitAI platform dashboard.
3.  **Generate MCP Configuration:** Run the following command in your terminal, replacing `YOUR_TRADERFIT_API_KEY_HERE` with the key you obtained:
    ```bash
    python -m traderfit_bridge.main --api-key YOUR_TRADERFIT_API_KEY_HERE --print-mcp-config
    ```
    *(Note: If `python` doesn't work, try `python3`)*

4.  **Copy the Output:** The command will print a JSON object similar to the example below. Copy this entire object.
    ```json
    {
        "mcpServers": {
            "traderfit": {
                "name": "TraderFit",
                "description": "TraderFitAI Bridge (via helper script)",
                "protocol": "stdio",
                "command": "/path/to/installed/traderfit-bridge", // Automatically detected path
                "cwd": "/path/to/parent/of/command", // Automatically detected path
                "env": {
                    "TRADERFIT_API_KEY": "YOUR_TRADERFIT_API_KEY_HERE", // Your key inserted here
                    "TRADERFIT_MCP_URL": "https://traderfit-mcp.skolp.com"
                }
            }
        }
    }
    ```
    *(The `command` and `cwd` paths will be automatically detected based on your installation.)*

5.  **Configure Cursor:** Open your Cursor configuration file (e.g., `~/.cursor/mcp.json`) and paste the copied JSON object into the `"mcpServers"` section (or merge it if the section already exists).
6.  **Reload MCP Clients:** Reload the clients in Cursor (e.g., via the command palette).

## Development Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/rizkisyaf/traderfit-bridge.git
    cd traderfit-bridge
    ```
2.  Create a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate 
    ```
3.  Install dependencies, including development tools:
    ```bash
    pip install -e ".[dev]" 
    ``` 
    *(Note: Requires defining `[project.optional-dependencies]` in pyproject.toml if you have dev tools like pytest, ruff, etc.)*

4. Create a `.env` file in the project root with your API key for local testing:
   ```dotenv
   TRADERFIT_API_KEY=YOUR_TRADERFIT_API_KEY_HERE
   TRADERFIT_MCP_URL=https://traderfit-mcp.skolp.com 
   # Optional: Set LOG_LEVEL=DEBUG for more verbose logging
   # LOG_LEVEL=DEBUG 
   ```

5. Run the bridge directly (for testing purposes):
   ```bash
   python -m traderfit_bridge.main 
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details (if one exists). 