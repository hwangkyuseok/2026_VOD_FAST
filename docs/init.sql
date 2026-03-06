-- Contextual Video Ad Insertion System — 초기 DB 스키마
-- PostgreSQL 16

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 작업(Job) 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status       VARCHAR(32)  NOT NULL DEFAULT 'pending',
    video_path   TEXT,
    error_message TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 씬 분석 결과 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS scene_analyses (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id         UUID        NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    scene_index    INT         NOT NULL,
    start_time     FLOAT       NOT NULL,
    end_time       FLOAT       NOT NULL,
    vision_tags    JSONB       NOT NULL DEFAULT '[]',
    transcript     TEXT,
    audio_features JSONB       NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scene_analyses_job_id ON scene_analyses (job_id);
CREATE INDEX IF NOT EXISTS idx_scene_analyses_scene_index ON scene_analyses (job_id, scene_index);

-- ============================================================
-- 광고 삽입 시점 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS insertion_points (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id       UUID        NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    timestamp    FLOAT       NOT NULL,
    confidence   FLOAT       NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    context_tags JSONB       NOT NULL DEFAULT '[]',
    reason       TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insertion_points_job_id ON insertion_points (job_id);
CREATE INDEX IF NOT EXISTS idx_insertion_points_timestamp ON insertion_points (job_id, timestamp);
