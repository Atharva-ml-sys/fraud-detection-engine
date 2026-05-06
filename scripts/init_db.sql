CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS transactions (
    id               SERIAL PRIMARY KEY,
    transaction_id   VARCHAR(100) UNIQUE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount           DECIMAL(15,2) NOT NULL,
    sender_account   VARCHAR(100) NOT NULL,
    receiver_account VARCHAR(100) NOT NULL,
    city             VARCHAR(100),
    risk_score       DECIMAL(5,2),
    risk_tier        VARCHAR(10),
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyst_feedback (
    id             SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100),
    analyst_id     VARCHAR(100),
    verdict        VARCHAR(30),
    notes          TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);

SELECT 'Database ready!' AS status;
