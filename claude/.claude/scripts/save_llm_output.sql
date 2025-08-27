-- Claude Code LLM Output Storage Schema
-- This table stores assistant responses from Claude Code sessions
-- for analysis and monitoring purposes

CREATE TABLE IF NOT EXISTS llm_outputs (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Timestamp when the output was saved
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- The actual LLM output text (required)
    output TEXT NOT NULL,
    
    -- Session identifier from Claude Code
    session_id VARCHAR(255),
    
    -- Repository identifier (e.g., github.com/user/repo)
    repository VARCHAR(500),
    
    -- Token usage statistics (nullable)
    input_tokens INTEGER,
    output_tokens INTEGER,
    
    -- Model information (nullable)
    model VARCHAR(100),
    service_tier VARCHAR(100)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_llm_outputs_created_at ON llm_outputs(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_outputs_session_id ON llm_outputs(session_id);
CREATE INDEX IF NOT EXISTS idx_llm_outputs_repository ON llm_outputs(repository);