# TraderFit Bridge (StdIO)

This package provides a Machine Cognition Protocol (MCP) bridge using standard input/output (stdio) to connect an MCP client (like Cursor) to the TraderFitAI backend API.

## Features

*   Dynamically fetches available tools from the TraderFitAI OpenAPI schema.
*   Executes tool calls by forwarding requests to the TraderFitAI API.
*   Authenticates with the backend using an API key provided via environment variable.

## Installation

```bash
# Coming soon to PyPI!
# pip install traderfit-bridge 
```

*(Currently, installation requires cloning the repository and setting up the environment manually - see Development Setup below)*

## Configuration (Command-Based - Current Method)

To use this bridge with Cursor, you need to configure it in your `~/.cursor/mcp.json` file within the `"mcpServers"` section. 

**Important:** You must replace the placeholder paths with the absolute paths on your local machine.

1.  Generate an API key from the TraderFitAI platform dashboard.
2.  Clone this repository: `git clone https://github.com/rizkisyaf/traderfit-bridge.git`
3.  Navigate into the directory: `cd traderfit-bridge`
4.  Create and activate a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate 
    ```
5.  Install dependencies: `pip install -e .` (Installs in editable mode)
6.  Find the absolute path to the installed `traderfit-bridge` executable (usually within `venv/bin/`) and the project's root directory (`pwd`).
7.  Add the following configuration to your `~/.cursor/mcp.json`, replacing placeholders:

```json
{
    "mcpServers": {
        "traderfit": {
            "name": "TraderFit",
            "description": "TraderFitAI Bridge (StdIO)",
            "protocol": "stdio",
            "command": "/absolute/path/to/your/traderfit-bridge/venv/bin/traderfit-bridge",
            "cwd": "/absolute/path/to/your/traderfit-bridge", 
            "env": {
                "TRADERFIT_API_KEY": "YOUR_TRADERFIT_API_KEY_HERE",
                "TRADERFIT_MCP_URL": "https://traderfit-mcp.skolp.com" 
            }
        }
        // ... other servers ...
    }
}
```

8. Reload MCP Clients in Cursor.

## Configuration (Package-Based - Future)

*(This method requires installing the package from PyPI: `pip install traderfit-bridge`)*

Once the package is installed, the bridge can be configured using a simple package reference in `~/.cursor/mcp.json`, **provided** you create a configuration file to store your API key.

1.  **Install the package:**
    ```bash
    pip install traderfit-bridge
    ```
2.  **Create the configuration directory (if it doesn't exist):**
    ```bash
    mkdir -p ~/.config/traderfit
    ```
3.  **Create and edit the configuration file:** `~/.config/traderfit/config.ini`
4.  **Add your credentials to the file:**
    ```ini
    [Credentials]
    api_key = YOUR_TRADERFIT_API_KEY_HERE
    # Optional: Override the default backend URL
    # backend_url = https://your-custom-backend.com
    ```
    Replace `YOUR_TRADERFIT_API_KEY_HERE` with the key generated from the TraderFitAI platform.

5.  **Configure Cursor (`~/.cursor/mcp.json`):**
    ```json
    {
        "mcpServers": {
            "traderfit": {
                "name": "TraderFit",
                "description": "TraderFitAI Bridge",
                "package": "traderfit-bridge", 
                "version": "0.1.1" // Or the specific version you installed
                // No command, cwd, or env needed here if config file is used
            }
            // ... other servers ...
        }
    }
    ```
6.  **Reload MCP Clients in Cursor.**

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