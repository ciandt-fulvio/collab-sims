-- CollabSims Database Schema for SQLite
-- Sessions, Events, and Activity Executions persistence

-- Sessions table (modified to support project-based sessions)
CREATE TABLE IF NOT EXISTS session (
    session_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,  -- References MD file in data/projects/
    session_name TEXT,  -- Auto-generated from first prompt (first 50 chars)
    agent_name TEXT,  -- Agent persona used in this session
    user_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'closed', 'error')),
    query_count INTEGER DEFAULT 0,
    metadata TEXT  -- JSON serialized metadata
);

CREATE INDEX IF NOT EXISTS idx_session_project ON session(project_name);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON session(user_id);
CREATE INDEX IF NOT EXISTS idx_session_created_at ON session(created_at);
CREATE INDEX IF NOT EXISTS idx_session_status ON session(status);

-- Events table (keep current structure)
CREATE TABLE IF NOT EXISTS event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    query_index INTEGER,
    message_id TEXT,
    data TEXT NOT NULL,  -- JSON serialized event data
    FOREIGN KEY (session_id) REFERENCES session(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_session_id ON event(session_id);
CREATE INDEX IF NOT EXISTS idx_event_event_type ON event(event_type);
CREATE INDEX IF NOT EXISTS idx_event_timestamp ON event(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_query_index ON event(session_id, query_index);

-- Activity executions table (new)
CREATE TABLE IF NOT EXISTS activity_execution (
    execution_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,  -- Project this activity belongs to
    activity_script TEXT NOT NULL,  -- Name of script MD file (without .md)
    session_id TEXT,  -- Session used to execute this activity (nullable)
    agent_names TEXT,  -- JSON array of agent names used
    status TEXT DEFAULT 'running' CHECK(status IN ('running', 'completed', 'error')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result_path TEXT,  -- Path to result MD file in data/activity_results/
    metadata TEXT,  -- JSON serialized metadata
    FOREIGN KEY (session_id) REFERENCES session(session_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_execution(project_name);
CREATE INDEX IF NOT EXISTS idx_activity_session ON activity_execution(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_status ON activity_execution(status);
CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_execution(created_at);
