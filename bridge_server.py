import sys
import os

# Ensure the src directory is in the Python path to find the package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'traderfit-mcp-stdio-bridge'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from traderfit_mcp_stdio_bridge.main import run_bridge

if __name__ == "__main__":
    run_bridge() 