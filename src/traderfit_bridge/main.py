import sys
print("TraderFit Bridge Starting...", file=sys.stderr)

import logging
import os
import asyncio
import httpx
from dotenv import load_dotenv
from openapi_pydantic import OpenAPI, PathItem, Operation
import mcp.types as types
from mcp.server.lowlevel.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from typing import Any, Dict, List, Optional, Tuple


# --- Remove config file imports --- #
# import configparser
# from pathlib import Path
# --- End Removal --- #

# --- Add imports for helper script --- #
import argparse
import json
import shutil
from pathlib import Path
# --- End imports --- #


# --- Global Logger Setup --- #
# Determine log level from environment variable, default to INFO
log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_name, logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create handlers
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(formatter)

# Ensure log file path is correct relative to script or cwd if needed
# Assuming cwd is TraderFitAI/ as set in mcp.json
# log_file_path = os.path.join(os.getcwd(), "traderfit-bridge", "bridge_server.log") 
# If cwd isn't reliable, use script directory:
# Calculate path relative to this script file (main.py)
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up two levels (src/traderfit_bridge -> traderfit-bridge)
project_root = os.path.dirname(os.path.dirname(script_dir))
log_file_path = os.path.join(project_root, "bridge_server.log")

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

file_handler = logging.FileHandler(log_file_path, mode='a') # Append mode
file_handler.setFormatter(formatter)

# Get the root logger and remove existing handlers (important!)
root_logger = logging.getLogger()
# Remove all handlers associated with the root logger object.
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
# Remove all handlers associated with the logger object from the previous run.
logger_instance = logging.getLogger("TraderFitStdioBridge")
for handler in logger_instance.handlers[:]:
    logger_instance.removeHandler(handler)


# Configure the specific logger
logger = logging.getLogger("TraderFitStdioBridge")
logger.setLevel(log_level) 
logger.addHandler(stderr_handler) # Keep stderr for immediate feedback if needed
logger.addHandler(file_handler)   # Add file logging
logger.propagate = False # Prevent messages from propagating to the root logger

logger.info(f"--- Bridge Restarting --- Logging configured. Level: {log_level_name}. File: {log_file_path} ---")
# ---> ADD EARLY LOG TEST <--- # Removed
logger.info("Logger initialization seems complete.")
# ---> END LOG TEST <--- #

# Prevent libraries (like httpx) from spamming debug logs unless explicitly desired
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --- Configuration Generation Function --- #
def print_mcp_json_config(api_key: str):
    """Generates and prints the command-based mcp.json configuration."""
    # --- Get the path to the current Python interpreter --- #
    python_executable_path = sys.executable 
    logger.info(f"Using Python executable: {python_executable_path}")

    # --- Calculate CWD based on the Python executable's location --- #
    # Assume structure like .../project_root/venv/bin/python
    # So, project root is 3 levels up from the python executable dir
    try:
        project_root_path = Path(python_executable_path).parent.parent.parent
        # Check if this looks like a plausible project root
        if (project_root_path / "pyproject.toml").is_file():
             cwd_path = str(project_root_path.resolve())
             logger.info(f"Calculated project root CWD: {cwd_path}")
        else:
             logger.warning("Could not reliably detect project root based on Python executable path. Using executable's parent directory as CWD.")
             cwd_path = str(Path(python_executable_path).parent.resolve())
    except Exception as e:
         logger.error(f"Error calculating CWD path: {e}. Using executable's parent directory.")
         cwd_path = str(Path(python_executable_path).parent.resolve())
    # --- End CWD Calculation --- #
    
    # Get backend URL from env or use default
    backend_url = os.getenv("TRADERFIT_MCP_URL", "https://traderfit-mcp.skolp.com")

    config = {
        "mcpServers": {
            "traderfit": {
                "name": "TraderFit",
                "description": "TraderFitAI Bridge (Python Module)", # Updated description
                "protocol": "stdio",
                "command": python_executable_path, # Use python path
                "args": ["-m", "traderfit_bridge.main"], # Add args to run module
                "cwd": cwd_path, 
                "env": {
                    "TRADERFIT_API_KEY": api_key,
                    "TRADERFIT_MCP_URL": backend_url
                }
            }
        }
    }
    print(json.dumps(config, indent=4))
# --- End Config Generation --- #


# --- Global Variables (consider class structure later) --- #
_openapi_schema: Optional[OpenAPI] = None
TRADERFIT_API_KEY: Optional[str] = None
TRADERFIT_PROD_URL: Optional[str] = None

# --- Helper to Fetch OpenAPI Schema --- #
async def get_openapi_schema() -> Optional[OpenAPI]:
    global _openapi_schema, TRADERFIT_API_KEY # Ensure API key is accessible
    if _openapi_schema:
        return _openapi_schema
    
    if not TRADERFIT_PROD_URL:
        logger.error("TRADERFIT_MCP_URL not configured.")
        return None
    if not TRADERFIT_API_KEY: # Check for API Key
        logger.error("TRADERFIT_API_KEY not configured.")
        return None

    schema_url = f"{TRADERFIT_PROD_URL}/openapi.json"
    headers = {"X-API-Key": TRADERFIT_API_KEY} # Add API Key header
    logger.info(f"Attempting to fetch OpenAPI schema from {schema_url} using API key.")
    try:
        async with httpx.AsyncClient() as client:
            # Increased timeout slightly
            response = await client.get(schema_url, headers=headers, timeout=20.0)
            logger.debug(f"Schema fetch response status: {response.status_code}")
            response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
            schema_data = response.json()
            _openapi_schema = OpenAPI.model_validate(schema_data)
            logger.info(f"Successfully fetched and parsed OpenAPI schema (version: {_openapi_schema.openapi})")
            return _openapi_schema
    except httpx.HTTPStatusError as e:
        # Log HTTP errors specifically
        logger.error(f"HTTP error fetching schema: {e.response.status_code} - Response: {e.response.text[:500]}", exc_info=True)
        return None
    except httpx.RequestError as e:
        # Log other request errors (timeouts, connection issues)
        logger.error(f"Request error fetching schema: {e}", exc_info=True)
        return None
    except Exception as e:
        # Log any other unexpected errors during fetch/parse
        logger.error(f"Unexpected error fetching/parsing OpenAPI schema: {e}", exc_info=True)
        return None

# --- Tool Listing Logic --- #
async def list_available_tools_impl() -> list[types.Tool]:
    # Restore simplified log message
    logger.info("list_tools handler called (dynamic - SIMPLIFIED TEST)") 
    schema = await get_openapi_schema()
    if not schema or not schema.paths:
        logger.error("OpenAPI schema not available or has no paths, returning empty tool list.")
        return []

    tools = []
    allowed_tags = {"CCXT", "Exchanges"}
    logger.debug(f"Filtering OpenAPI paths for tags: {allowed_tags}")

    for path, path_item in schema.paths.items():
        operations: List[Tuple[str, Optional[Operation]]] = [
            ("get", path_item.get), ("post", path_item.post), ("put", path_item.put),
            ("delete", path_item.delete), ("patch", path_item.patch)
        ]
        for http_method, operation in operations:
            if operation and operation.tags and allowed_tags.intersection(operation.tags):
                tool_name = operation.operationId
                if not tool_name:
                    continue # Skip tools without explicit IDs
                
                # --- Generate Tool Definition with Proper Input Schema --- #
                logger.debug(f"Generating tool definition for: {tool_name}")

                # Prepare input schema properties and required list
                input_properties = {}
                input_required = []

                if operation.parameters:
                    logger.debug(f"  Processing {len(operation.parameters)} parameters for {tool_name}")
                    for param in operation.parameters:
                        # Basic type mapping (can be expanded)
                        param_type = "string" # Default type
                        param_format = None # Default format
                        # Safely access schema attributes only if schema_ exists
                        if hasattr(param, "schema_") and param.schema_:
                            param_type = param.schema_.type or "string" # Use schema type or default
                            param_format = param.schema_.format # Get format if available
                        # TODO: Add handling for param.content if needed for complex parameters
                        
                        if param_type == "integer": json_type = "integer"
                        elif param_type == "number": json_type = "number"
                        elif param_type == "boolean": json_type = "boolean"
                        # TODO: Handle array, object types if needed
                        else: json_type = "string"

                        # Safely get parameter location and required status
                        param_in = getattr(param, 'in_', 'unknown')
                        param_required = getattr(param, 'required', False)

                        input_properties[param.name] = {
                            "type": json_type,
                            "description": param.description or f"{param_in} parameter: {param.name}"
                        }
                        # Add format if available and obtained safely
                        if param_format:
                            input_properties[param.name]["format"] = param_format
                        
                        if param_required: # Use safe param_required
                            input_required.append(param.name)
                        logger.debug(f"    - Param: {param.name} (in: {param_in}, type: {json_type}, required: {param_required})")

                # Handle requestBody (basic handling for application/json)
                # Note: MCP clients might handle request bodies differently than simple params.
                # This adds body parameters to the same input schema for simplicity here.
                if operation.requestBody and operation.requestBody.content:
                    json_content = operation.requestBody.content.get('application/json')
                    # --- Use hasattr() to check for schema_ --- #
                    if json_content and hasattr(json_content, "schema_") and json_content.schema_ and hasattr(json_content.schema_, "properties") and json_content.schema_.properties:
                        logger.debug(f"  Processing requestBody properties for {tool_name}")
                        for prop_name, prop_schema in json_content.schema_.properties.items():
                            prop_type = prop_schema.type or 'string'
                            if prop_type == "integer": json_prop_type = "integer"
                            elif prop_type == "number": json_prop_type = "number"
                            elif prop_type == "boolean": json_prop_type = "boolean"
                            elif prop_type == "array": json_prop_type = "array"
                            # TODO: Handle nested objects in body more robustly if needed
                            else: json_prop_type = "string"

                            input_properties[prop_name] = {
                                "type": json_prop_type,
                                "description": prop_schema.description or f"Body property: {prop_name}"
                            }
                            # Add format if available
                            if prop_schema.format:
                                input_properties[prop_name]["format"] = prop_schema.format
                            # Add enum if available
                            if prop_schema.enum:
                                input_properties[prop_name]["enum"] = prop_schema.enum
                                
                            logger.debug(f"    - Body Prop: {prop_name} (type: {json_prop_type})")
                        # Check for required body properties
                        if json_content.schema_.required:
                            for req_prop in json_content.schema_.required:
                                if req_prop not in input_required: # Avoid duplicates
                                    input_required.append(req_prop)
                                    logger.debug(f"    - Body Prop Required: {req_prop}")

                # Construct the final input schema
                input_schema = {"type": "object"}
                if input_properties:
                    input_schema["properties"] = input_properties
                if input_required:
                    input_schema["required"] = input_required

                # --- Use SIMPLIFIED TOOL DEFINITION (Bypass complex parsing) --- # REMOVED
                # logger.debug(f\"Generating BASIC tool definition for: {tool_name}\")
                tool = types.Tool(
                    name=tool_name,
                    description=operation.summary or f"{http_method.upper()} {path}", # Use original description
                    # Always provide a minimal valid schema: # REMOVED
                    inputSchema=input_schema, # Use the generated schema
                    outputSchema={"type": "object"} # Keep output schema simple for now
                )
                # --- End SIMPLIFIED TOOL DEFINITION --- # # REMOVED
                tools.append(tool)

    if not tools:
        logger.warning(f"No tools generated from schema. Check paths, tags ({allowed_tags}), and operationIds in the OpenAPI spec.")
    else:
        # Restore simplified log message
        logger.info(f"Successfully generated {len(tools)} BASIC tools from OpenAPI schema.")
    return tools

# --- Tool Execution Logic --- #
async def execute_tool_impl(name: str, arguments: Dict[str, Any] | None) -> List[types.TextContent]:
    # ---> ADD ENTRY LOGGING <--
    logger.debug(f"[execute_tool_impl N:{name}] ENTERED function. Args: {arguments}")
    # ---> END LOGGING <--
    log_prefix = f"[execute_tool_impl N:{name}]"
    # ---> Log Script Path <---\
    logger.info(f"{log_prefix} EXECUTING SCRIPT: {__file__}")
    logger.info(f"{log_prefix} EXECUTE TOOL HANDLER CALLED. Args: {arguments}") 

    if not arguments: arguments = {} # Ensure arguments is always a dict

    if not TRADERFIT_API_KEY or not TRADERFIT_PROD_URL:
        logger.error(f"{log_prefix} API Key or URL not configured for tool execution.")
        return [types.TextContent(type="text", text="Error: Bridge not configured correctly (API Key/URL missing).")]

    schema = await get_openapi_schema() # Re-fetch schema if needed (or rely on global)
    if not schema or not schema.paths:
        logger.error(f"{log_prefix} Cannot execute tool: OpenAPI schema unavailable.")
        return [types.TextContent(type="text", text="Error: Cannot determine API endpoint. OpenAPI schema unavailable.")]
    
    api_path = None
    http_method = None
    path_params = {}
    query_params = {}
    request_body = None

    # Find the operation matching the tool name (operationId)
    found_op = False
    original_schema_path = None # Store the original path template for reference
    for path, path_item in schema.paths.items():
        if found_op: break
        operations: List[Tuple[str, Optional[Operation]]] = [
            ("GET", path_item.get), ("POST", path_item.post), ("PUT", path_item.put), 
            ("DELETE", path_item.delete), ("PATCH", path_item.patch)
        ]
        for method, operation in operations:
            if operation and operation.operationId == name:
                http_method = method
                original_schema_path = path # Store the path from the schema

                # List of refactored operation IDs that now use /by-name and exchange_name query param
                refactored_tool_names = {
                    # Use the full operationId names from the API schema
                    "get_exchange_balance_by_name", 
                    "get_exchange_ticker_by_name", 
                    "get_exchange_ohlcv_by_name", 
                    "get_exchange_order_book_by_name",
                    "get_exchange_funding_rate_by_name", 
                    "get_exchange_my_trades_by_name", 
                    "get_exchange_open_orders_by_name",
                    "get_exchange_closed_orders_by_name", 
                    "get_exchange_positions_by_name", 
                    # These were likely correct already, but ensure consistency
                    "delete_exchange_key", 
                    "sync_exchange_trades", 
                    "disconnect_exchange"
                }

                # --- NEW LOGIC for /by-name endpoints ---
                if name in refactored_tool_names:
                    logger.info(f"{log_prefix} Entered /by-name logic for {name}") 
                    # Determine the correct /by-name path structure
                    # --- FIX: Use the path directly from the schema for /by-name tools --- 
                    api_path = original_schema_path 
                    logger.debug(f"{log_prefix} Tool '{name}' uses path directly from schema: {api_path}")
                    # --- REMOVE OLD/INCORRECT PATH CONSTRUCTION ---
                    # if name == "delete_exchange_key":
                    #     api_path = f"/api/exchange-keys/by-name"
                    # elif name == "sync_exchange_trades":
                    #     api_path = f"/api/exchanges/sync/by-name"
                    # elif name == "disconnect_exchange":
                    #     api_path = f"/api/exchanges/disconnect/by-name"
                    # else: # Assume others follow the /api/exchanges/data/.../by-name pattern
                    #     # Extract the data type (e.g., 'balance', 'ticker') from the original path
                    #     # ---> ADD LOGGING FOR ORIGINAL PATH <---
                    #     logger.debug(f"{log_prefix} For tool '{name}', original_schema_path is: {original_schema_path}")
                    #     # ---> END LOGGING <---
                    #     path_parts = original_schema_path.split('/')
                    #     # Example original path: '/api/exchanges/data/{connection_id}/balance'
                    #     # We expect the data type to be the last part
                    #     if len(path_parts) > 0:
                    #          data_type = path_parts[-1]
                    #          api_path = f"/api/exchanges/data/{data_type}/by-name"
                    #          logger.info(f"{log_prefix} Constructed /by-name data path: {api_path}")
                    #     else:
                    #          logger.error(f"{log_prefix} Could not determine data type from original path '{original_schema_path}' for tool '{name}'")
                    #          logger.warning(f"{log_prefix} Returning early due to path determination error.")
                    #          return [types.TextContent(text="ERROR_HANDLER_REACHED_PATH_DETERMINATION")]
                    # logger.debug(f"{log_prefix} Tool '{name}' uses '/by-name' path: {api_path}") 
                    # --- END REMOVAL ---

                    # Extract exchange_name for query params (Mandatory for these tools)
                    if "exchange_name" not in arguments:
                        logger.error(f"{log_prefix} Missing required parameter 'exchange_name' for tool '{name}'")
                        logger.warning(f"{log_prefix} Returning early due to missing exchange_name.")
                        return [types.TextContent(type="text", text="ERROR_HANDLER_REACHED_MISSING_EXCHANGE_NAME")]
                    query_params["exchange_name"] = arguments["exchange_name"]

                    # Extract other potential query/body params based on OpenAPI spec
                    if operation.parameters:
                        for param in operation.parameters:
                            # Skip path params (like connection_id) and exchange_name (already handled)
                            # --- Safely check param.in_ --- #
                            param_location = getattr(param, 'in_', 'unknown')
                            if param_location == "path" or param.name == "exchange_name": continue
                            
                            if param.name in arguments:
                                if param_location == "query": # Use safe param_location
                                    query_params[param.name] = arguments[param.name]
                                # Note: Body params are handled via requestBody below, not here

                    # Handle request body (e.g., for sync_trades)
                    if operation.requestBody:
                        # Extract args that aren't exchange_name and aren't defined as query params
                        potential_body_args = {k: v for k, v in arguments.items() if k != "exchange_name" and k not in query_params}
                        # We should ideally check against the requestBody schema, but for now, assume these are body args
                        if potential_body_args:
                            request_body = potential_body_args
                            logger.debug(f"{log_prefix} Identified request body for {name}: {request_body}")

                # --- ORIGINAL LOGIC for other endpoints ---
                else:
                    api_path = original_schema_path # Use the original path from schema
                    logger.info(f"{log_prefix} Using standard path: {api_path}")
                    logger.debug(f"{log_prefix} Tool '{name}' uses standard path: {api_path}")
                if operation.parameters:
                    for param in operation.parameters:
                            # --- Safely check param.in_ --- #
                            param_location = getattr(param, 'in_', 'unknown')
                            if param.name in arguments:
                                if param_location == "path": # Use safe param_location
                                    path_params[param.name] = arguments[param.name]
                            elif param_location == "query": # Use safe param_location
                                query_params[param.name] = arguments[param.name]
                if operation.requestBody:
                    body_args = {k: v for k, v in arguments.items() if k not in path_params and k not in query_params}
                    if body_args: request_body = body_args

                found_op = True
                break # Exit the inner loop (methods)

    if not found_op:
        logger.error(f"Could not find API endpoint details for tool '{name}' in schema.")
        return [types.TextContent(text=f"Error: Configuration error for tool '{name}'. Is the operationId correct in the schema and bridge filter?")]
    if not api_path or not http_method: # Should be set if found_op is True
        logger.error(f"Internal error: Found operation for '{name}' but path or method is missing.")
        return [types.TextContent(text=f"Internal bridge error processing tool '{name}'.")]

    # --- FIX: Apply path parameter formatting HERE for non-/by-name routes --- #
    formatted_path = api_path # Start with the determined path (could be /by-name or template)
    if path_params: # Only format if path_params were extracted (i.e., it's NOT a /by-name route)
        # --- Indent the try...except block --- #
        try:
            formatted_path = api_path.format(**path_params)
            logger.debug(f"Formatted path with params for '{name}': {formatted_path}")
        except KeyError as e:
            logger.error(f"Missing path parameter '{e}' for tool '{name}' in arguments: {arguments}")
            return [types.TextContent(text=f"Error: Missing required path parameter '{e}' for tool '{name}'.")]
    # --- END FIX --- #

    # Construct the final URL using the (potentially) formatted path
    api_url = f"{TRADERFIT_PROD_URL}{formatted_path}"

    # *** Ensure the correct header name is used ***
    # Common alternatives: "Authorization": f"Bearer {TRADERFIT_API_KEY}"
    headers = {"X-API-Key": TRADERFIT_API_KEY}
    
    # ---> ADD LOGGING FOR FINAL URL <---
    logger.info(f"{log_prefix} Attempting to call final URL: {http_method} {api_url}")
    # ---> END LOGGING <---

    logger.debug(f"{log_prefix} Making API call: {http_method} {api_url} | Query: {query_params} | Body: {request_body} | Headers: {list(headers.keys())}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=http_method,
                url=api_url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_body if request_body else None,
                timeout=60.0
            )
            logger.debug(f"{log_prefix} API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.debug(f"{log_prefix} API Response Data (type {type(data)}): {str(data)[:500]}...")
            return [types.TextContent(type="text", text=f"Success: {data}")]
        except httpx.HTTPStatusError as e:
            logger.error(f"{log_prefix} HTTP error calling API: {e.response.status_code} - {e.response.text[:500]}", exc_info=True)
            error_detail = e.response.text # Default to full text
            try:
                # Try to parse JSON error detail for cleaner output
                error_json = e.response.json()
                if isinstance(error_json, dict) and 'detail' in error_json:
                    error_detail = error_json['detail']
            except Exception:
                pass # Keep original text if JSON parsing fails
            return [types.TextContent(type="text", text=f"Error: API call failed ({e.response.status_code}): {error_detail}")]
        except httpx.RequestError as e:
            logger.error(f"{log_prefix} Request error calling API: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: Could not connect to API: {e}")]
        except Exception as e:
            logger.error(f"{log_prefix} Unexpected error during tool execution: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: An unexpected error occurred in the bridge: {e}")]

# --- Main Bridge Function (called by entry point) --- #
async def run_bridge():
    # --- Simplified Configuration Loading (Env Vars Only) --- #
    logger.info("Loading configuration from environment...")
    # Load .env first (useful for local dev testing when not run by MCP client)
    load_dotenv()
    
    global TRADERFIT_API_KEY, TRADERFIT_PROD_URL

    TRADERFIT_API_KEY = os.getenv("TRADERFIT_API_KEY")
    TRADERFIT_PROD_URL = os.getenv("TRADERFIT_MCP_URL")

    logger.info(f"API Key from environment: {'Found' if TRADERFIT_API_KEY else 'Not Found'}")
    logger.info(f"Backend URL from environment: {'Found' if TRADERFIT_PROD_URL else 'Not Found'}")

    # Use default URL if not found in env
    if not TRADERFIT_PROD_URL:
        TRADERFIT_PROD_URL = "https://traderfit-mcp.skolp.com"
        logger.info(f"Using default Backend URL: {TRADERFIT_PROD_URL}")

    # Final Check for API Key
    if not TRADERFIT_API_KEY:
        error_msg = (
            "CRITICAL ERROR: TRADERFIT_API_KEY environment variable not set!\n"
            "This bridge expects the API key to be provided by the MCP client environment."
        )
        logger.critical(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    # --- End Simplified Configuration Loading --- #

    # --- Original Initialization Logic --- #
    logger.info(f"--- TraderFit StdIO Bridge Initializing ---")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"API Key Loaded: {'Yes'}")
    logger.info(f"Target API URL: {TRADERFIT_PROD_URL}")

    try:
        # Create the MCP Server Instance
        # Update version string if needed
        server = Server(name="TraderFit", version="0.1.1") 
        logger.info(f"MCP Server instance '{server.name}' created.")

        # Decorate handlers
        list_tools_handler = server.list_tools()(list_available_tools_impl)
        call_tool_handler = server.call_tool()(execute_tool_impl)

        # Await stdio_server directly
        logger.info("Creating InitializationOptions...")
        init_options = server.create_initialization_options()
        logger.info("InitializationOptions created.")
        
        logger.info("Starting stdio_server context manager...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio_server streams obtained. Running server.run()...")
            await server.run(read_stream, write_stream, init_options)
            logger.info("server.run() finished.") 

    except ImportError as e:
        logger.critical(f"CRITICAL IMPORT ERROR: {e}", exc_info=True)
        print(f"ImportError: {e}. Please ensure all dependencies are installed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during bridge setup/run: {e}", exc_info=True)
        print(f"Critical runtime error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        logger.info("--- TraderFit StdIO Bridge Shutting Down --- ")
        logging.shutdown()

# --- Main Execution Block (Handles both running the bridge and printing config) --- #
def main():
    parser = argparse.ArgumentParser(description="TraderFit MCP Bridge or Config Helper")
    parser.add_argument("--api-key", type=str, help="Your TraderFit API Key.")
    parser.add_argument("--print-mcp-config", action="store_true", help="Print the mcp.json configuration snippet and exit.")

    args = parser.parse_args()
    # ---> ADD LOGGING to see parsed args <--- #
    # Use a temporary basic config for logging just in case logger isn't fully set up yet
    logging.basicConfig(level=logging.INFO) 
    logging.info(f"Parsed args: {args}")
    # ---> END LOGGING <--- #

    if args.print_mcp_config:
        if not args.api_key:
            print("Error: --api-key is required when using --print-mcp-config", file=sys.stderr)
            sys.exit(1)
        print_mcp_json_config(args.api_key)
        # No need to exit here, function completes
    else:
        # Default action: Run the bridge
        logger.info("Running the async bridge...")
        try:
            # Ensure the logger used by run_bridge is configured before calling it
            # (The setup at the top of the file should handle this)
            asyncio.run(run_bridge())
        except Exception as e:
            # Use logger if available, otherwise print
            log_func = logger.critical if logger else print
            log_func(f"Unhandled exception during bridge run: {e}", exc_info=True)
            sys.exit(1) # Exit with error code if bridge crashes
        finally:
             if logger:
                  logger.info("Async bridge run finished or exited.")

if __name__ == "__main__":
    main()