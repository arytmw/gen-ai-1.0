# Simple banking MCP example — Python SDK v2

A small server and client, following the structure of the original
[simple_mcp example](https://github.com/networknuts/gen-ai-10.0/tree/main/mcp/simple_mcp).
The server exposes exactly three MCP tools: `get_balance`, `get_transactions`, and
`block_card`. There are no MCP resources or MCP prompts.

The client discovers the tools, gives their schemas to OpenAI, calls the selected
tool through MCP, and prints its result. Like the original, this is one query per
run and at most one tool call, without a second model request to rewrite the result.
The OpenAI instructions in the client are ordinary model instructions, not an MCP prompt.

```text
client.py → MCP server.py (:8000) → FastAPI banking_api.py (:8080) → PostgreSQL (:5433)
```

Docker Compose runs PostgreSQL; `init.sql` creates and seeds the three tables.
`banking_api.py` queries PostgreSQL with Psycopg and returns JSON.
`server.py` exposes the three MCP tools as small HTTP wrappers around that API.
`client.py` discovers and calls the MCP tools, as before.
Only PostgreSQL runs in Docker; the three Python programs run on your machine.

## Setup

Use Python 3.10 or newer (the commands below use Python 3.11) and Docker with the
Compose plugin. Start Docker before running this demo. From the course root:

```bash
cd 10-mcp-for-devops/banking_mcp_v2
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Put your OpenAI API key in `.env`. The model defaults to `gpt-5.4-mini`, as in the
original example; `OPENAI_MODEL` can override it. This example has its own requirements
and virtual environment because the existing course examples use MCP v1.

The `DATABASE_URL` in `.env.example` matches the local demo credentials and port
in `compose.yaml`. If you already have a `.env`, add that line instead of replacing
your existing API key. PostgreSQL is bound to localhost port **5433** to avoid
conflicting with a local database on 5432.

## Run

Start PostgreSQL in the background and wait for it to become healthy:

```bash
docker compose up -d --wait
docker compose ps
```

The first startup runs `init.sql` automatically. A named volume retains the data
on subsequent starts. Editing `init.sql` does not change an existing database.

In terminal 1, from this directory with the virtual environment activated:

```bash
python -m uvicorn banking_api:app --host 127.0.0.1 --port 8080
```

Explore the banking API at [Swagger UI](http://127.0.0.1:8080/docs).

In terminal 2, from the same directory:

```bash
source .venv/bin/activate
python server.py
```

The MCP server listens at `http://localhost:8000/mcp` using Streamable HTTP.

In terminal 3, from the same directory:

```bash
source .venv/bin/activate
python client.py
```

## Demo queries and expected outputs

Enter these queries at `Enter banking query:`. Run `python client.py` again for
each query; the client does not retain conversation history. Card state now persists
in PostgreSQL across API, MCP server, and database restarts. Use the card reset
command below if you want both cards to start as active.

These are user queries, not registered MCP prompts. The tool results below match
the sample data and implementation. Model selection and clarification wording can
vary; these natural-language queries have not been tested against the live OpenAI API.
The client prints tool output as JSON, without asking the model to summarize it.

### 1. Check a balance

Query: `What is the balance of account 1001?`

Expected call: `get_balance(account_id="1001")`

Expected console output:

```text
LLM SELECTED TOOL: get_balance
{
  "account_id": "1001",
  "holder": "Asha Sharma",
  "account_type": "savings",
  "balance": "25000.00",
  "currency": "INR"
}
```

Try `What is the balance of account 1002?` to get Rohan Mehta's `current` account,
with `"balance": "48000.00"` and `"currency": "INR"`.

Money is stored as PostgreSQL `NUMERIC(12,2)` and returned as decimal strings in
JSON to preserve exact values, including paise, without floating-point conversion.

### 2. Get the latest two transactions

Query: `Show the last 2 transactions for account 1002.`

Expected call: `get_transactions(account_id="1002", limit=2)`

Expected console output:

```text
LLM SELECTED TOOL: get_transactions
{
  "account_id": "1002",
  "currency": "INR",
  "total": 4,
  "transactions": [
    {
      "id": "txn_008",
      "date": "2026-09-17",
      "description": "Vendor payment",
      "amount": "-5000.00"
    },
    {
      "id": "txn_007",
      "date": "2026-09-16",
      "description": "Internet bill",
      "amount": "-2000.00"
    }
  ]
}
```

`total` is the number of available transactions, not the number returned.
Negative amounts are debits. With `Show transactions for account 1001.`, the default
limit is 5, so all four transactions are returned, newest first:

| Date | Description | Amount (INR) |
|---|---|---|
| 2026-09-17 | Groceries | -1,000 |
| 2026-09-16 | Rent | -4,000 |
| 2026-09-15 | Salary | 30,000 |
| 2026-09-14 | ATM withdrawal | -10,000 |

### 3. Block a stolen card

Query: `Block my card card_1001 because it was stolen.`

Expected call: `block_card(card_id="card_1001", reason="stolen")`

Expected console output on the first block:

```text
LLM SELECTED TOOL: block_card
{
  "card_id": "card_1001",
  "account_id": "1001",
  "last_four": "4321",
  "type": "debit",
  "status": "blocked",
  "reason": "stolen",
  "blocked_at": "<actual UTC timestamp>",
  "message": "Card blocked successfully"
}
```

`blocked_at` contains the real time of the API call, such as an ISO 8601 timestamp
ending in `+00:00`; the placeholder above is illustrative.

### 4. Repeat the block request

Query: `Block my card card_1001.`

Run this after example 3 without resetting the card in the database. The expected output
has the same card details, original `"reason": "stolen"`, and original `blocked_at`,
with `"message": "Card is already blocked"`.

### 5. Block the other card without a reason

Query: `Please block card card_1002.`

Expected call: `block_card(card_id="card_1002")`, or the same call with
`reason="requested"` explicitly supplied. If that card is active, expect
`"status": "blocked"`, `"reason": "requested"`, `"last_four": "8765"`,
`"account_id": "1002"`, a new `blocked_at`, and
`"message": "Card blocked successfully"`.

### 6. Missing information and error cases

| Query / setup | Expected behavior |
|---|---|
| `What is my balance?` | No tool call; the model should ask for an account ID. Example: `Please provide your account ID.` |
| `Please block my card.` | No tool call; the model should ask for a card ID. Example: `Which card ID would you like to block?` |
| `What is the balance of account 9999?` | Selects `get_balance`; prints `TOOL ERROR:` with `Banking API error (404): Account not found`. |
| `Block my card card_9999.` | Selects `block_card`; prints `TOOL ERROR:` with `Banking API error (404): Card not found`. |
| Stop only the banking API, then ask `What is the balance of account 1001?` | Selects `get_balance`; prints `TOOL ERROR:` with `Banking API is unavailable. Start banking_api.py on port 8080.` |
| Run `docker compose stop db`, then ask `What is the balance of account 1001?` | FastAPI returns HTTP 503; MCP prints a tool error containing `Banking database is unavailable`. Start it again with `docker compose up -d --wait`. |

The SDK may add an `Error executing tool ...` prefix to error text. To answer a
clarification, rerun the client with the complete request, such as
`What is the balance of account 1001?`; entering just `1001` starts a new query.

For a validation demo, try `Show the last 25 transactions for account 1001.`
The model may explain the 1–20 limit instead of calling the tool. If it sends
`limit=25`, the API returns HTTP 422 and the client prints a tool error containing
the validation details. To demonstrate that error deterministically, use:

```bash
curl 'http://127.0.0.1:8080/accounts/1001/transactions?limit=25'
```

Keep each query focused on one operation: the current client supports at most one
tool call per run. A request such as `Check my balance and block my card` will not
reliably demonstrate both operations in this example.

## Sample banking API

| Account | Holder | Type | Balance | Card | Last four |
|---|---|---|---|---|---|
| `1001` | Asha Sharma | Savings | INR 25,000 | `card_1001` | 4321 |
| `1002` | Rohan Mehta | Current | INR 48,000 | `card_1002` | 8765 |

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/accounts/{account_id}/balance` | Balance calculated from opening balance and transactions |
| GET | `/accounts/{account_id}/transactions?limit=5` | Most recent first; limit must be 1–20 |
| POST | `/cards/{card_id}/block` | JSON body: `{"reason": "stolen"}` |

Card blocking accepts `lost`, `stolen`, `suspicious_activity`, or `requested`.
Send `{}` to use `requested`. The response includes the card's account, last four
digits, status, reason, and UTC block time. Repeated requests preserve the first
block's reason and timestamp.

Try the API directly without an OpenAI key:

```bash
curl http://127.0.0.1:8080/accounts/1001/balance
curl 'http://127.0.0.1:8080/accounts/1002/transactions?limit=2'
curl -X POST http://127.0.0.1:8080/cards/card_1001/block \
  -H 'Content-Type: application/json' -d '{"reason":"stolen"}'
```

All bank data is fictional and stored in PostgreSQL. Negative transaction amounts
represent debits. Unknown IDs return HTTP 404, invalid inputs return HTTP 422, and
database connection failures return HTTP 503; MCP forwards these as tool errors.
This is a teaching example with local demo database credentials, no API
authentication, and no real bank connection.

## Database walkthrough

`init.sql` contains three tables: `accounts`, `transactions`, and `cards`.
Foreign keys link transactions and cards to accounts. The balance query sums the
account's opening balance and its transactions. An index supports account-based
transaction lookups in newest-first order.

Psycopg's `dict_row` produces Python dictionaries from query results; FastAPI
serializes them into JSON. SQL parameters use `%s` placeholders with separate
argument tuples. The API uses synchronous route functions for the synchronous
database driver, with one connection and transaction per request.

Card blocking locks the selected row with `FOR UPDATE`, checks its status, and
updates it in the same transaction. Concurrent block requests preserve the first
successful block's reason and timestamp. Successful requests commit; exceptions
roll back and connections close.

Inspect the data directly:

```bash
docker compose exec db psql -U banking -d banking
```

Then run:

```sql
SELECT * FROM accounts;
SELECT * FROM transactions ORDER BY account_id, date DESC;
SELECT card_id, status, reason, blocked_at FROM cards;
```

Exit `psql` with `\q`. To reset just the demo cards to active:

```bash
docker compose exec db psql -U banking -d banking -c \
  "UPDATE cards SET status = 'active', reason = NULL, blocked_at = NULL;"
```

Stop the database and remove its container while retaining data:

```bash
docker compose down
```

To deliberately **delete all demo database data** and seed a fresh database:

```bash
docker compose down -v
docker compose up -d --wait
```

The named volume survives `down`; `down -v` removes it. The SQL initialization
script runs only when the volume is empty.

## What changed from SDK v1?

| v1 | v2 |
|---|---|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` |
| `FastMCP(...)` | `MCPServer(...)` |
| `FastMCP(..., json_response=True)` | `mcp.run(..., json_response=True)` |
| Transport context + `ClientSession` + `initialize()` | `async with Client(url)` |
| `tool.inputSchema` | `tool.input_schema` |
| `result.structuredContent` / `result.isError` | `result.structured_content` / `result.is_error` |

The `@mcp.tool()` decorators and `call_tool(name, arguments)` pattern remain familiar.
This uses the official `mcp` Python SDK v2 package.

References: [SDK v2 changes](https://py.sdk.modelcontextprotocol.io/whats-new/),
[MCP client](https://py.sdk.modelcontextprotocol.io/client/), and
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).
