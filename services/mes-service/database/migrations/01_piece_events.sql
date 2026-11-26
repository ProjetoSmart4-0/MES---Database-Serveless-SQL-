-- Executar SOMENTE após confirmar a estrutura de pieces_traceability.
-- Migração aditiva: não remove nem modifica tabelas existentes.
CREATE TABLE IF NOT EXISTS piece_events (
    id BIGSERIAL PRIMARY KEY,
    qr_code TEXT NOT NULL REFERENCES pieces_traceability(qr_code),
    event_type VARCHAR(50) NOT NULL,
    details TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_piece_events_qr_time ON piece_events(qr_code, occurred_at);
