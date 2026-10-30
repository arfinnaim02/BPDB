BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_foundation

CREATE TABLE daily_reports (
    report_date DATE NOT NULL, 
    dataset_grain VARCHAR(80) NOT NULL, 
    current_version_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_daily_reports PRIMARY KEY (id), 
    CONSTRAINT uq_daily_report_grain UNIQUE (report_date, dataset_grain)
);

CREATE INDEX ix_daily_reports_report_date ON daily_reports (report_date);

CREATE TABLE dataset_versions (
    sha256 VARCHAR(64) NOT NULL, 
    cutoff_date DATE NOT NULL, 
    row_count INTEGER NOT NULL, 
    member_version_ids JSON NOT NULL, 
    export_storage_key TEXT, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_dataset_versions PRIMARY KEY (id), 
    CONSTRAINT uq_dataset_versions_sha256 UNIQUE (sha256)
);

CREATE TABLE ingestion_runs (
    status VARCHAR(20) NOT NULL, 
    trigger VARCHAR(20) NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    statistics JSON NOT NULL, 
    error_code VARCHAR(80), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ingestion_runs PRIMARY KEY (id), 
    CONSTRAINT ck_ingestion_runs_status CHECK (status IN ('running','succeeded','failed','partial'))
);

CREATE TABLE daily_report_versions (
    report_id VARCHAR(36) NOT NULL, 
    version_number INTEGER NOT NULL, 
    quality_status VARCHAR(20) NOT NULL, 
    parser_version VARCHAR(80) NOT NULL, 
    available_at TIMESTAMP WITH TIME ZONE, 
    correction_reason TEXT, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_daily_report_versions PRIMARY KEY (id), 
    CONSTRAINT ck_daily_report_versions_quality_status CHECK (quality_status IN ('validated','partial','quarantined','conflict')), 
    CONSTRAINT ck_daily_report_versions_positive_version CHECK (version_number > 0), 
    CONSTRAINT fk_daily_report_versions_report_id_daily_reports FOREIGN KEY(report_id) REFERENCES daily_reports (id), 
    CONSTRAINT uq_report_version_identity UNIQUE (report_id, id), 
    CONSTRAINT uq_report_version_number UNIQUE (report_id, version_number)
);

CREATE INDEX ix_daily_report_versions_report_id ON daily_report_versions (report_id);

CREATE TABLE source_documents (
    original_url TEXT NOT NULL, 
    category VARCHAR(80) NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    storage_key TEXT NOT NULL, 
    original_filename TEXT NOT NULL, 
    content_type VARCHAR(100) NOT NULL, 
    size_bytes INTEGER NOT NULL, 
    report_date DATE, 
    archive_date_hint DATE, 
    published_at TIMESTAMP WITH TIME ZONE, 
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    parser_version VARCHAR(80), 
    status VARCHAR(20) NOT NULL, 
    ingestion_run_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_source_documents PRIMARY KEY (id), 
    CONSTRAINT ck_source_documents_checksum_length CHECK (length(sha256) = 64), 
    CONSTRAINT ck_source_documents_positive_size CHECK (size_bytes > 0), 
    CONSTRAINT fk_source_documents_ingestion_run_id_ingestion_runs FOREIGN KEY(ingestion_run_id) REFERENCES ingestion_runs (id), 
    CONSTRAINT uq_source_url_checksum UNIQUE (original_url, sha256)
);

CREATE INDEX ix_source_documents_sha256 ON source_documents (sha256);

CREATE TABLE cost_observations (
    fuel VARCHAR(80) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    zone VARCHAR(80) NOT NULL, 
    period VARCHAR(80) NOT NULL, 
    value NUMERIC(24, 6), 
    unit VARCHAR(40) NOT NULL, 
    source_page INTEGER, 
    raw_text TEXT, 
    CONSTRAINT pk_cost_observations PRIMARY KEY (id), 
    CONSTRAINT fk_cost_observations_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_cost_observations_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id), 
    CONSTRAINT uq_cost_grain UNIQUE (version_id, metric, zone, period, unit, fuel)
);

CREATE INDEX ix_cost_observations_version_id ON cost_observations (version_id);

CREATE TABLE demand_observations (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    zone VARCHAR(80) NOT NULL, 
    period VARCHAR(80) NOT NULL, 
    value NUMERIC(24, 6), 
    unit VARCHAR(40) NOT NULL, 
    source_page INTEGER, 
    raw_text TEXT, 
    CONSTRAINT pk_demand_observations PRIMARY KEY (id), 
    CONSTRAINT fk_demand_observations_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_demand_observations_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id), 
    CONSTRAINT uq_demand_grain UNIQUE (version_id, metric, zone, period, unit)
);

CREATE INDEX ix_demand_observations_version_id ON demand_observations (version_id);

CREATE TABLE extraction_issues (
    source_id VARCHAR(36) NOT NULL, 
    version_id VARCHAR(36), 
    code VARCHAR(80) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    details JSON NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_extraction_issues PRIMARY KEY (id), 
    CONSTRAINT fk_extraction_issues_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_extraction_issues_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id)
);

CREATE INDEX ix_extraction_issues_source_id ON extraction_issues (source_id);

CREATE TABLE fuel_observations (
    fuel VARCHAR(80) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    zone VARCHAR(80) NOT NULL, 
    period VARCHAR(80) NOT NULL, 
    value NUMERIC(24, 6), 
    unit VARCHAR(40) NOT NULL, 
    source_page INTEGER, 
    raw_text TEXT, 
    CONSTRAINT pk_fuel_observations PRIMARY KEY (id), 
    CONSTRAINT fk_fuel_observations_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_fuel_observations_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id), 
    CONSTRAINT uq_fuel_grain UNIQUE (version_id, metric, zone, period, unit, fuel)
);

CREATE INDEX ix_fuel_observations_version_id ON fuel_observations (version_id);

CREATE TABLE generation_observations (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    zone VARCHAR(80) NOT NULL, 
    period VARCHAR(80) NOT NULL, 
    value NUMERIC(24, 6), 
    unit VARCHAR(40) NOT NULL, 
    source_page INTEGER, 
    raw_text TEXT, 
    CONSTRAINT pk_generation_observations PRIMARY KEY (id), 
    CONSTRAINT fk_generation_observations_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_generation_observations_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id), 
    CONSTRAINT uq_generation_grain UNIQUE (version_id, metric, zone, period, unit)
);

CREATE INDEX ix_generation_observations_version_id ON generation_observations (version_id);

CREATE TABLE load_shedding_observations (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    zone VARCHAR(80) NOT NULL, 
    period VARCHAR(80) NOT NULL, 
    value NUMERIC(24, 6), 
    unit VARCHAR(40) NOT NULL, 
    source_page INTEGER, 
    raw_text TEXT, 
    CONSTRAINT pk_load_shedding_observations PRIMARY KEY (id), 
    CONSTRAINT fk_load_shedding_observations_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_load_shedding_observations_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id), 
    CONSTRAINT uq_load_shedding_grain UNIQUE (version_id, metric, zone, period, unit)
);

CREATE INDEX ix_load_shedding_observations_version_id ON load_shedding_observations (version_id);

CREATE TABLE version_sources (
    version_id VARCHAR(36) NOT NULL, 
    source_id VARCHAR(36) NOT NULL, 
    CONSTRAINT pk_version_sources PRIMARY KEY (version_id, source_id), 
    CONSTRAINT fk_version_sources_source_id_source_documents FOREIGN KEY(source_id) REFERENCES source_documents (id), 
    CONSTRAINT fk_version_sources_version_id_daily_report_versions FOREIGN KEY(version_id) REFERENCES daily_report_versions (id)
);

ALTER TABLE daily_reports ADD CONSTRAINT fk_daily_current_version FOREIGN KEY(id, current_version_id) REFERENCES daily_report_versions (report_id, id);

INSERT INTO alembic_version (version_num) VALUES ('0001_foundation') RETURNING alembic_version.version_num;

COMMIT;

