-- OAS Checker e-service Database Schema
-- PostgreSQL schema for validation tracking and rate limiting

-- Validations table
-- Stores validation request metadata and status
CREATE TABLE IF NOT EXISTS validations (
    "id" TEXT PRIMARY KEY,
    "status" TEXT NOT NULL,
    "ruleset" TEXT NOT NULL,
    "ruleset_version" TEXT NOT NULL,
    "errors_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "format" TEXT NOT NULL DEFAULT 'json',
    "file_sha256" TEXT NOT NULL,
    "file_content" TEXT NOT NULL,
    "report_content" JSONB,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL,
    "completed_at" TIMESTAMP WITH TIME ZONE,
    "error_message" TEXT
);

-- Indexes for validations table
CREATE INDEX IF NOT EXISTS idx_validations_status ON validations("status");
CREATE INDEX IF NOT EXISTS idx_validations_created_at ON validations("created_at");
CREATE INDEX IF NOT EXISTS idx_validations_file_sha256 ON validations("file_sha256");

-- Rate limiting tracking table
-- Tracks API requests per consumer per endpoint using fixed window algorithm
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    "id" SERIAL PRIMARY KEY,
    "consumer_id" TEXT NOT NULL,
    "endpoint" TEXT NOT NULL,
    "request_count" INTEGER NOT NULL DEFAULT 1,
    "window_start" TIMESTAMP WITH TIME ZONE NOT NULL,
    "window_end" TIMESTAMP WITH TIME ZONE NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE("consumer_id", "endpoint", "window_start")
);

-- Indexes for rate_limit_tracking table
CREATE INDEX IF NOT EXISTS idx_rate_limit_consumer_endpoint ON rate_limit_tracking("consumer_id", "endpoint");
CREATE INDEX IF NOT EXISTS idx_rate_limit_window_end ON rate_limit_tracking("window_end");
CREATE INDEX IF NOT EXISTS idx_rate_limit_created_at ON rate_limit_tracking("created_at");
