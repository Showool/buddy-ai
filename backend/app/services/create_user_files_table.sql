-- 用户文件表
CREATE TABLE IF NOT EXISTS user_files (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_content BYTEA NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, original_filename)
);

-- 创建用户ID索引
CREATE INDEX IF NOT EXISTS idx_user_files_user_id ON user_files(user_id);

-- 创建文件ID索引
CREATE INDEX IF NOT EXISTS idx_user_files_file_id ON user_files(id);