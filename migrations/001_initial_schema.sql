-- Run this in Supabase SQL Editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- OPD Units
CREATE TABLE opd_units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opd_code        TEXT NOT NULL,
    name            TEXT NOT NULL,
    kabupaten       TEXT NOT NULL,
    total_budget    NUMERIC(18,2),
    fiscal_year     INTEGER
);

-- Documents
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    storage_path    TEXT,
    document_type   TEXT NOT NULL CHECK (document_type IN ('apbd','spj','procurement','contract')),
    fiscal_year     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','complete','error')),
    error_message   TEXT,
    page_count      INTEGER,
    item_count      INTEGER,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ
);

-- Budget Items
CREATE TABLE budget_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    opd_id          UUID REFERENCES opd_units(id),
    item_code       TEXT,
    item_name       TEXT NOT NULL,
    budget_amount   NUMERIC(18,2),
    realized_amount NUMERIC(18,2),
    item_type       TEXT CHECK (item_type IN ('belanja','pendapatan','pembiayaan')),
    sub_type        TEXT,
    source_page     INTEGER,
    raw_data        JSONB
);

-- Vendors
CREATE TABLE vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    npwp            TEXT,
    address         TEXT,
    bank_account    TEXT,
    bank_name       TEXT,
    is_flagged      BOOLEAN NOT NULL DEFAULT FALSE
);

-- Procurement Transactions
CREATE TABLE procurement_transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    opd_id              UUID REFERENCES opd_units(id),
    vendor_id           UUID REFERENCES vendors(id),
    contract_number     TEXT,
    item_description    TEXT NOT NULL,
    category            TEXT CHECK (category IN ('konstruksi','konsultansi','barang','jasa_lainnya')),
    procurement_method  TEXT CHECK (procurement_method IN ('tender','penunjukan_langsung','pengadaan_langsung')),
    contract_value      NUMERIC(18,2),
    shsr_benchmark      NUMERIC(18,2),
    contract_date       DATE,
    work_start_date     DATE,
    work_end_date       DATE,
    spj_date            DATE,
    payment_date        DATE,
    fiscal_year         INTEGER,
    raw_data            JSONB
);

-- Findings
CREATE TABLE findings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    opd_id              UUID REFERENCES opd_units(id),
    budget_item_id      UUID REFERENCES budget_items(id),
    transaction_id      UUID REFERENCES procurement_transactions(id),
    source              TEXT NOT NULL CHECK (source IN ('compliance_scan','procurement_anomaly')),
    finding_type        TEXT NOT NULL,
    risk_level          TEXT NOT NULL CHECK (risk_level IN ('red','yellow','green')),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    regulation_refs     JSONB,
    evidence            JSONB,
    ai_explanation      TEXT,
    confidence_score    NUMERIC(3,2),
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','dismissed')),
    confirmed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit Memos
CREATE TABLE audit_memos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opd_id          UUID REFERENCES opd_units(id),
    fiscal_year     INTEGER NOT NULL,
    finding_ids     UUID[],
    storage_path    TEXT,
    format          TEXT NOT NULL DEFAULT 'docx' CHECK (format IN ('docx','pdf')),
    memo_number     TEXT,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Regulations (metadata)
CREATE TABLE regulations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    peraturan_number TEXT NOT NULL,
    full_title       TEXT NOT NULL,
    category         TEXT CHECK (category IN ('pengadaan','keuangan_daerah','anggaran')),
    effective_date   DATE,
    chunk_count      INTEGER,
    indexed_at       TIMESTAMPTZ
);

-- Regulation Chunks (pgvector)
CREATE TABLE regulation_chunks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id    UUID NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
    peraturan_number TEXT NOT NULL,
    pasal            TEXT,
    content          TEXT NOT NULL,
    embedding        vector(768),
    topic_tags       TEXT[]
);

CREATE INDEX ON regulation_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- SHSR Benchmarks
CREATE TABLE shsr_benchmarks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kabupaten        TEXT,
    item_code        TEXT,
    item_description TEXT NOT NULL,
    unit             TEXT,
    price            NUMERIC(18,2) NOT NULL,
    fiscal_year      INTEGER NOT NULL
);

-- Chat Sessions
CREATE TABLE chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chat Messages
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content         TEXT NOT NULL,
    regulation_refs JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_findings_document_id ON findings(document_id);
CREATE INDEX idx_findings_opd_id ON findings(opd_id);
CREATE INDEX idx_findings_risk_level ON findings(risk_level);
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_procurement_opd_vendor ON procurement_transactions(opd_id, vendor_id);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
