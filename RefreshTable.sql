-- Drop existing tables (in correct order due to foreign key constraints)
DROP TABLE IF EXISTS score_history CASCADE;
DROP TABLE IF EXISTS frame_data CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create frame_data table with composite primary key
CREATE TABLE frame_data (
    user_id INTEGER NOT NULL REFERENCES users(id),
    frame_id INTEGER NOT NULL,
    score FLOAT DEFAULT 0,
    PRIMARY KEY (user_id, frame_id)
);

-- Create score_history table with composite primary key
CREATE TABLE score_history (
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score FLOAT DEFAULT 0,
    PRIMARY KEY (user_id, created_at)
);

-- Add indexes for better query performance
CREATE INDEX idx_frame_data_user_id ON frame_data(user_id);
CREATE INDEX idx_score_history_user_id ON score_history(user_id);
CREATE INDEX idx_users_username ON users(username); 