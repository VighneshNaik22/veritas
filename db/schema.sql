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

CREATE TABLE outbox (
  outbox_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  refund_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  queued_at TEXT NOT NULL,
  sent_at TEXT
);

CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE otp_challenges (
  challenge_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  otp_hash TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  used_at REAL,
  request_ip TEXT NOT NULL
);

INSERT INTO customers (customer_id, name, eligible) VALUES ('C123', 'Asha Rao', 1);
INSERT INTO customers (customer_id, name, eligible) VALUES ('C124', 'Ravi Kumar', 1);
INSERT INTO users (user_id, email, created_at)
VALUES ('demo-user', 'demo@example.com', strftime('%s', 'now'));