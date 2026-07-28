DROP TABLE IF EXISTS requests CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS extracted_fields CASCADE;
DROP TABLE IF EXISTS proposed_actions CASCADE;
DROP TABLE IF EXISTS action_log CASCADE;

CREATE TABLE requests (
    id          SERIAL PRIMARY KEY,
    raw_text    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',
    category    TEXT,
    urgency     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id            INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    product       TEXT NOT NULL,
    amount_cents  INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'delivered'
);

CREATE TABLE extracted_fields(
    id  SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    fields  JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE proposed_actions(
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()  
);

CREATE TABLE action_log(
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    step TEXT NOT NULL,
    detail JSONB NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

