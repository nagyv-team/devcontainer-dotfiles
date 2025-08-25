-- Create table for storing user prompts from Claude Code
-- This table is used by the save_user_prompt.py hook script

CREATE TABLE IF NOT EXISTS user_prompts (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    prompt TEXT NOT NULL,
    session_id VARCHAR(255),
    repository VARCHAR(500)
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_user_prompts_created_at ON user_prompts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_prompts_session_id ON user_prompts(session_id);
CREATE INDEX IF NOT EXISTS idx_user_prompts_repository ON user_prompts(repository);

-- Add comment to the table
COMMENT ON TABLE user_prompts IS 'Stores user prompts submitted to Claude Code via the UserPromptSubmit hook';
COMMENT ON COLUMN user_prompts.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN user_prompts.created_at IS 'Timestamp when the prompt was submitted';
COMMENT ON COLUMN user_prompts.prompt IS 'The actual user prompt text';
COMMENT ON COLUMN user_prompts.session_id IS 'Claude Code session UUID if available';
COMMENT ON COLUMN user_prompts.repository IS 'Git repository in format: host/user/repo (e.g., github.com/user/repo)';