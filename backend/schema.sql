-- Run against the database named by DB_NAME in backend/.env.
-- The application creates these same missing tables automatically on startup.
-- Existing tables are never dropped. All DATETIME values are UTC.

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash VARCHAR(64) NOT NULL PRIMARY KEY,
    user_id INT NOT NULL,
    expires_at DATETIME NOT NULL,
    INDEX ix_auth_sessions_user_id (user_id),
    INDEX ix_auth_sessions_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash VARCHAR(64) NOT NULL PRIMARY KEY,
    user_id INT NOT NULL,
    expires_at DATETIME NOT NULL,
    INDEX ix_password_reset_tokens_user_id (user_id),
    INDEX ix_password_reset_tokens_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
