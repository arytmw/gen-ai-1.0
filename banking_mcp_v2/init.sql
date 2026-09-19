-- Runs once, when Docker initializes an empty database volume.
BEGIN;

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    holder TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('savings', 'current')),
    currency TEXT NOT NULL DEFAULT 'INR' CHECK (currency = 'INR'),
    opening_balance NUMERIC(12, 2) NOT NULL
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount <> 0)
);

CREATE INDEX transactions_account_date_idx ON transactions (account_id, date DESC, id DESC);

CREATE TABLE cards (
    card_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    last_four TEXT NOT NULL CHECK (last_four ~ '^[0-9]{4}$'),
    type TEXT NOT NULL DEFAULT 'debit' CHECK (type IN ('debit', 'credit')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
    reason TEXT CHECK (reason IN ('lost', 'stolen', 'suspicious_activity', 'requested')),
    blocked_at TIMESTAMPTZ,
    CHECK (
        (status = 'active' AND reason IS NULL AND blocked_at IS NULL)
        OR (status = 'blocked' AND reason IS NOT NULL AND blocked_at IS NOT NULL)
    )
);

CREATE INDEX cards_account_idx ON cards (account_id);

INSERT INTO accounts (account_id, holder, account_type, currency, opening_balance) VALUES
    ('1001', 'Asha Sharma', 'savings', 'INR', 10000.00),
    ('1002', 'Rohan Mehta', 'current', 'INR', 20000.00);

-- Negative amounts are debits; positive amounts are credits.
INSERT INTO transactions (id, account_id, date, description, amount) VALUES
    ('txn_001', '1001', '2026-09-14', 'ATM withdrawal', -10000.00),
    ('txn_002', '1001', '2026-09-15', 'Salary', 30000.00),
    ('txn_003', '1001', '2026-09-16', 'Rent', -4000.00),
    ('txn_004', '1001', '2026-09-17', 'Groceries', -1000.00),
    ('txn_005', '1002', '2026-09-14', 'Client payment', 40000.00),
    ('txn_006', '1002', '2026-09-15', 'Office supplies', -5000.00),
    ('txn_007', '1002', '2026-09-16', 'Internet bill', -2000.00),
    ('txn_008', '1002', '2026-09-17', 'Vendor payment', -5000.00);

INSERT INTO cards (card_id, account_id, last_four) VALUES
    ('card_1001', '1001', '4321'),
    ('card_1002', '1002', '8765');

COMMIT;
