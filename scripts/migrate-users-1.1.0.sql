-- ============================================================================
-- PaperMind · 存量库迁移脚本 · 1.1.0（Beta 多用户隔离：users 表 + 外键）
-- ============================================================================
-- 谁执行：P6 刘征（数据/部署）
-- 适用：**已经建好的老库**（全新库直接走 docs/契约/03-数据库表结构.sql，无需本脚本）
-- 幂等：可重复执行，不报错、不产生脏数据
--
-- 执行方式（在项目根目录）：
--   docker compose exec -T postgres psql -U papermind -d papermind < scripts/migrate-users-1.1.0.sql
-- ============================================================================

-- 1) users 表（已存在则跳过）
CREATE TABLE IF NOT EXISTS users (
    id                BIGSERIAL    PRIMARY KEY,
    username          TEXT         NOT NULL UNIQUE,          -- 登录名，全库唯一
    password_hash     TEXT         NOT NULL,                 -- bcrypt 哈希，不存明文
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- 2) legacy 占位账号（id=1）：Alpha 所有 papers 都挂在 user_id=1 下，
--    先落这个账号，外键才能成立；不用于登录。
INSERT INTO users (id, username, password_hash)
VALUES (1, 'legacy', '!disabled')
ON CONFLICT (id) DO NOTHING;

-- 3) 序列拨正：显式插了 id=1，序列不会自动前进，否则下一个注册用户会撞 id=1
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- 4) 兜底：无主论文（user_id 不是合法用户）统一归 legacy，保证外键能建上
UPDATE papers SET user_id = 1 WHERE user_id NOT IN (SELECT id FROM users);

-- 5) 加外键（幂等：PostgreSQL 没有 ADD CONSTRAINT IF NOT EXISTS，用 DO 块兜底）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_papers_user'
    ) THEN
        ALTER TABLE papers
            ADD CONSTRAINT fk_papers_user
            FOREIGN KEY (user_id) REFERENCES users(id);
    END IF;
END $$;
