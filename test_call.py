import httpx
import os
import asyncio
from dotenv import load_dotenv

async def main():
    # Load environment variables from .env file in the current directory
    load_dotenv()

    api_key = os.getenv("TRADERFIT_API_KEY")
    base_url = os.getenv("TRADERFIT_MCP_URL", "https://traderfit-mcp.skolp.com")

    if not api_key:
        print("Error: TRADERFIT_API_KEY not found in environment/.env")
        return
    if not base_url:
        print("Error: TRADERFIT_MCP_URL not found in environment/.env")
        return

    # --- Test Configuration ---
    exchange = "bybit"
    # Construct the CORRECT URL directly
    target_url = f"{base_url}/api/exchanges/data/balance/by-name?exchange_name={exchange}"
    headers = {"X-API-Key": api_key}
    # --------------------------

    print(f"--- Minimal Test Script ---")
    print(f"Target URL: GET {target_url}")
    print(f"Using API Key: {api_key[:8]}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, headers=headers, timeout=30.0)
            print(f"\nResponse Status Code: {response.status_code}")

            try:
                # Try to print JSON, otherwise print text
                response_data = response.json()
                print("Response JSON:")
                import json
                print(json.dumps(response_data, indent=2))
            except Exception:
                print("Response Text:")
                print(response.text)

    except httpx.HTTPStatusError as e:
        print(f"\nHTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except httpx.RequestError as e:
        print(f"\nRequest Error: {e}")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
