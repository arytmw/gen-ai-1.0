import os
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv(Path(__file__).with_name(".env"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://banking:banking_demo@127.0.0.1:5433/banking")
app = FastAPI(title="Sample Banking API", version="2.0.0")


@contextmanager
def database():
    # Commit on success, roll back on errors, and always close the connection.
    try:
        with psycopg.connect(
            DATABASE_URL, row_factory=dict_row, connect_timeout=5, options="-c timezone=UTC"
        ) as connection:
            yield connection
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        raise HTTPException(status_code=503, detail="Banking database is unavailable") from exc


class BlockCardRequest(BaseModel):
    reason: Literal["lost", "stolen", "suspicious_activity", "requested"] = "requested"


@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: str):
    """Calculate the balance in PostgreSQL and return it as JSON."""
    with database() as connection:
        account = connection.execute(
            """
            SELECT account_id, holder, account_type, currency,
                   (opening_balance + COALESCE(
                       (SELECT SUM(amount) FROM transactions WHERE account_id = a.account_id), 0
                   ))::text AS balance
            FROM accounts AS a WHERE account_id = %s
            """,
            (account_id,),
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return account


@app.get("/accounts/{account_id}/transactions")
def get_transactions(account_id: str, limit: int = Query(default=5, ge=1, le=20)):
    """Read the most recent transactions from PostgreSQL."""
    with database() as connection:
        account = connection.execute(
            "SELECT currency FROM accounts WHERE account_id = %s", (account_id,)
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        total = connection.execute(
            "SELECT COUNT(*) AS total FROM transactions WHERE account_id = %s", (account_id,)
        ).fetchone()["total"]
        recent = connection.execute(
            """
            SELECT id, date::text, description, amount::text
            FROM transactions WHERE account_id = %s
            ORDER BY date DESC, id DESC LIMIT %s
            """,
            (account_id, limit),
        ).fetchall()
        return {"account_id": account_id, "currency": account["currency"], "total": total, "transactions": recent}


@app.post("/cards/{card_id}/block")
def block_card(card_id: str, request: BlockCardRequest):
    """Persist a card block; repeated requests preserve the first block's details."""
    with database() as connection:
        # Lock this card until commit so concurrent requests cannot overwrite a block.
        card = connection.execute(
            "SELECT * FROM cards WHERE card_id = %s FOR UPDATE", (card_id,)
        ).fetchone()
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        if card["status"] == "blocked":
            return {**card, "message": "Card is already blocked"}
        card = connection.execute(
            """
            UPDATE cards SET status = 'blocked', reason = %s, blocked_at = CURRENT_TIMESTAMP
            WHERE card_id = %s RETURNING *
            """,
            (request.reason, card_id),
        ).fetchone()
        return {**card, "message": "Card blocked successfully"}
