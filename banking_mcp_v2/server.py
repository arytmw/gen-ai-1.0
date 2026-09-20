import requests
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("Banking Assistant")
BANKING_API_URL = "http://127.0.0.1:8080"


def call_banking_api(method, path, params=None, json=None):
    # Shared HTTP request and error handling for all three tools.
    try:
        response = requests.request(
            method, f"{BANKING_API_URL}{path}", params=params, json=json, timeout=5
        )
    except requests.RequestException as exc:
        raise ToolError("Banking API is unavailable. Start banking_api.py on port 8080.") from exc

    if not response.ok:
        raise ToolError(f"Banking API error ({response.status_code}): {response.json()['detail']}")
    return response.json()


@mcp.tool()
def get_balance(account_id: str):
    """Get the balance, currency, and account holder for a bank account."""
    return call_banking_api("GET", f"/accounts/{account_id}/balance")


@mcp.tool()
def get_transactions(account_id: str, limit: int = 5):
    """Get recent transactions, newest first. Limit: 1-20. Negative amounts are debits."""
    return call_banking_api(
        "GET", f"/accounts/{account_id}/transactions", params={"limit": limit}
    )


@mcp.tool()
def block_card(card_id: str, reason: str = "requested"):
    """Block a card only on request. Reason: lost, stolen, suspicious_activity, or requested."""
    return call_banking_api(
        "POST", f"/cards/{card_id}/block", json={"reason": reason}
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", json_response=True)
