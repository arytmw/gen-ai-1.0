from typing import Any, Literal
from urllib.parse import quote

import requests
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("Banking Assistant")
BANKING_API_URL = "http://127.0.0.1:8080"


def call_banking_api(method: str, path: str, **kwargs) -> dict[str, Any]:
    """Make an HTTP request and report API failures as MCP tool errors."""
    try:
        response = requests.request(method, f"{BANKING_API_URL}{path}", timeout=5, **kwargs)
    except requests.RequestException as exc:
        raise ToolError("Banking API is unavailable. Start banking_api.py on port 8080.") from exc

    if not response.ok:
        raise ToolError(f"Banking API error ({response.status_code}): {response.json()['detail']}")
    return response.json()


@mcp.tool()
def get_balance(account_id: str) -> dict[str, Any]:
    """Get the balance, currency, and account holder for a bank account."""
    return call_banking_api("GET", f"/accounts/{quote(account_id, safe='')}/balance")


@mcp.tool()
def get_transactions(account_id: str, limit: int = 5) -> dict[str, Any]:
    """Get recent transactions, newest first. Limit: 1–20. Negative amounts are debits."""
    return call_banking_api(
        "GET", f"/accounts/{quote(account_id, safe='')}/transactions", params={"limit": limit}
    )


@mcp.tool()
def block_card(
    card_id: str,
    reason: Literal["lost", "stolen", "suspicious_activity", "requested"] = "requested",
) -> dict[str, Any]:
    """Block a card only when the user explicitly asks. Include their reason if provided."""
    return call_banking_api(
        "POST", f"/cards/{quote(card_id, safe='')}/block", json={"reason": reason}
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", json_response=True)
