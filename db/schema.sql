CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  eligible INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE refunds (
  refund_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  idempotency_key TEXT
);

CREATE TABLE sent_emails (
  email_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  refund_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  sent_at TEXT NOT NULL
);

CREATE TABLE audit_log (
  log_id TEXT PRIMARY KEY,
  step_id TEXT NOT NULL,
  message TEXT NOT NULL,
  logged_at TEXT NOT NULL
);

INSERT INTO customers (customer_id, name, eligible) VALUES ('C123', 'Asha Rao', 1);
INSERT INTO customers (customer_id, name, eligible) VALUES ('C124', 'Ravi Kumar', 1);