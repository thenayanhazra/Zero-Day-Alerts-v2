CREATE TABLE raw_items (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(120) NOT NULL,
    source_url VARCHAR(1024) NOT NULL,
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL,
    content_hash VARCHAR(128) NOT NULL UNIQUE
);

CREATE INDEX idx_raw_items_source_name ON raw_items(source_name);
CREATE INDEX idx_raw_items_source_url ON raw_items(source_url);
CREATE INDEX idx_raw_items_collected_at ON raw_items(collected_at);
CREATE INDEX idx_raw_items_content_hash ON raw_items(content_hash);

CREATE TABLE canonical_events (
    id SERIAL PRIMARY KEY,
    event_key VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(512) NOT NULL,
    summary TEXT,
    normalized_payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_canonical_events_event_key ON canonical_events(event_key);

CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES canonical_events(id) ON DELETE CASCADE,
    model_name VARCHAR(128) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scores_event_id ON scores(event_id);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES canonical_events(id) ON DELETE CASCADE,
    channel VARCHAR(64) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    sent_at TIMESTAMP,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_alerts_event_id ON alerts(event_id);
CREATE INDEX idx_alerts_channel ON alerts(channel);
CREATE INDEX idx_alerts_status ON alerts(status);

CREATE TABLE source_health (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    latency_ms INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_checked_at TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_source_health_status ON source_health(status);
