-- ============================================================================
-- PaperMind · 数据库表结构契约（PostgreSQL 16 + pgvector）
-- ============================================================================
-- 谁和谁的约定：P6 刘征（建表） ↔ P4 刘万礼（读写 papers） ↔ P5 吴啸天（读写 chunks）
-- 版本：1.0.0-frozen   冻结日期：2026-10-24（P1 裁定提前冻结）
--
-- 【它管什么】
--   三个人的代码都往这几张表读写，字段名错一个字母就查不出来。
--   本文件就是唯一标准：名字、类型、能不能空、默认值、约束、索引，全在这里。
--
-- 【五条全局约定】
--   1. 命名一律 snake_case（parse_status，不是 parseStatus）
--   2. 主键统一 BIGSERIAL；外键统一 BIGINT
--   3. 时间统一 TIMESTAMPTZ，默认 now()，不要用不带时区的 TIMESTAMP
--   4. 页码 page 一律从 1 开始
--   5. 枚举值用 CHECK 约束锁死，不许写文档外的值
--
-- 【启动方式】
--   docker compose up -d 后，本文件由 postgres 容器首次启动自动执行
--   （compose 里挂载到 /docker-entrypoint-initdb.d/01-schema.sql）
--   手动执行：psql -U papermind -d papermind -f 03-数据库表结构.sql
-- ============================================================================

-- pgvector 扩展：向量检索靠它，必须最先建
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- 表 1：papers —— 论文元数据（一篇 PDF 一行）
-- 谁写：P4（上传时插入、解析后更新状态）
-- 谁读：P4（列表、详情）、P5（解析时取 file_path）
-- ============================================================================
CREATE TABLE IF NOT EXISTS papers (
    id                BIGSERIAL    PRIMARY KEY,

    -- Alpha 阶段不做登录，固定为 1；Beta 接真实用户后再用
    user_id           BIGINT       NOT NULL DEFAULT 1,

    title             TEXT         NOT NULL,                 -- 默认取文件名，P4 可后续支持手动改
    filename          TEXT         NOT NULL,                 -- 原始文件名，用于前端显示
    file_path         TEXT         NOT NULL,                 -- 磁盘绝对路径，**不对外暴露**
    file_size_bytes   BIGINT       NOT NULL DEFAULT 0,       -- 文件大小，前端做展示

    page_count        INT          NOT NULL DEFAULT 0,       -- 总页数，解析完成后回写
    chunk_count       INT          NOT NULL DEFAULT 0,       -- 段落数，解析完成后回写

    -- 解析状态：这条是「前端能不能提问」的唯一依据
    -- pending 已入库未开始 / parsing 解析中 / ready 可提问 / failed 解析失败
    parse_status      TEXT         NOT NULL DEFAULT 'pending'
                      CHECK (parse_status IN ('pending', 'parsing', 'ready', 'failed')),
    parse_error       TEXT,                                  -- failed 时记录原因，排查用

    -- 来源：本地上传 or Beta 阶段从学术库检索导入
    source            TEXT         NOT NULL DEFAULT 'upload'
                      CHECK (source IN ('upload', 'arxiv', 'openalex', 'semanticscholar', 'crossref')),

    -- ↓ 以下三个为 Beta「关键词检索导入」预留，Alpha 一律为空
    doi               TEXT,
    arxiv_id          TEXT,
    external_url      TEXT,                                  -- 原文落地页；非 OA 时只给这个链接

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  papers               IS '论文元数据，一篇 PDF 一行';
COMMENT ON COLUMN papers.file_path     IS '磁盘绝对路径，禁止通过接口直接暴露，取文件必须走 /api/papers/{id}/file';
COMMENT ON COLUMN papers.parse_status  IS 'pending=待解析, parsing=解析中, ready=可提问, failed=解析失败';
COMMENT ON COLUMN papers.source        IS 'upload=本地上传；其余为 Beta 检索导入来源';
COMMENT ON COLUMN papers.external_url  IS '外部来源原文链接，非开放获取时前端只展示该链接，不下载全文';

-- 列表页按「新建的在上」排序，这条索引直接服务该查询
CREATE INDEX IF NOT EXISTS idx_papers_user_created
    ON papers (user_id, created_at DESC);

-- 前端轮询解析状态时按 id 查，主键已覆盖；这里给状态过滤留一条
CREATE INDEX IF NOT EXISTS idx_papers_parse_status
    ON papers (parse_status);


-- ============================================================================
-- 表 2：chunks —— 论文切片与向量（供 RAG 检索）
-- 谁写：P5（解析时批量插入）
-- 谁读：P5（向量检索）
-- ============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    id                BIGSERIAL    PRIMARY KEY,

    -- 论文删除时级联删掉它的段落，避免孤儿数据
    paper_id          BIGINT       NOT NULL
                      REFERENCES papers(id) ON DELETE CASCADE,

    chunk_index       INT          NOT NULL,                 -- 在本文中的顺序，从 0 开始
    page              INT          NOT NULL CHECK (page >= 1), -- 所在页，**从 1 开始**
    content           TEXT         NOT NULL,                 -- 原文片段
    char_count        INT,                                   -- 字数，便于调试切片效果
    token_count       INT,                                   -- token 数，便于估算成本

    -- ↓ 引用高亮框：Alpha 阶段全部为 NULL，Beta 阶段由 P5 填充
    --   归一化 0~1，相对单页宽高，左上原点，x 向右、y 向下
    bbox_x0           DOUBLE PRECISION CHECK (bbox_x0 BETWEEN 0 AND 1),
    bbox_y0           DOUBLE PRECISION CHECK (bbox_y0 BETWEEN 0 AND 1),
    bbox_x1           DOUBLE PRECISION CHECK (bbox_x1 BETWEEN 0 AND 1),
    bbox_y1           DOUBLE PRECISION CHECK (bbox_y1 BETWEEN 0 AND 1),

    -- 向量列：**维度必须与 embedding 模型一致**
    -- 当前约定 1024 维（bge-m3）。换模型必须重建整列 + 重新解析所有论文。
    embedding         vector(1024),

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- 同一篇论文里 chunk_index 不能重复，防止重复解析产生脏数据
    UNIQUE (paper_id, chunk_index)
);

COMMENT ON TABLE  chunks            IS '论文切片与向量，RAG 检索的数据源';
COMMENT ON COLUMN chunks.page       IS '所在页码，从 1 开始，前端据此跳转';
COMMENT ON COLUMN chunks.bbox_x0    IS '引用框左上 x，归一化 0~1；Alpha 为 NULL，Beta 填充';
COMMENT ON COLUMN chunks.embedding  IS '向量，维度必须等于 1024（与 bge-m3 一致），换模型需重建';

-- 按论文过滤后再做向量检索，这条是必备索引
CREATE INDEX IF NOT EXISTS idx_chunks_paper
    ON chunks (paper_id);

-- 向量索引：先不建，原因如下
--   1. Alpha 数据量小（几篇论文、几百片段），顺序扫描比建索引更快
--   2. ivfflat / hnsw 需要先有数据再建才能保证效果
--   3. 建错索引反而拖慢，Beta 阶段数据量上来后再按下面这条建：
--
-- CREATE INDEX idx_chunks_embedding ON chunks
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);
--
-- 检索时必须用同一个距离算子：向量用 cosine，
-- SQL 写法：ORDER BY embedding <=> $1 LIMIT 3


-- ============================================================================
-- 表 3：reading_session —— 阅读行为（RC 阶段「学术阅读周报」的数据源）
-- Alpha 阶段：**只建空表，不写入**
-- ============================================================================
CREATE TABLE IF NOT EXISTS reading_session (
    id                BIGSERIAL    PRIMARY KEY,
    user_id           BIGINT       NOT NULL DEFAULT 1,
    paper_id          BIGINT       NOT NULL
                      REFERENCES papers(id) ON DELETE CASCADE,

    started_at        TIMESTAMPTZ  NOT NULL,                 -- 开始阅读时间
    ended_at          TIMESTAMPTZ,                           -- 结束时间，可为空（异常退出）
    duration_sec      INT          NOT NULL DEFAULT 0,       -- 阅读时长（秒）
    pages_viewed      INT          NOT NULL DEFAULT 0,       -- 本次浏览页数

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE reading_session IS '阅读行为记录；Alpha 只建表不写入，RC 阶段做阅读周报看板用';

CREATE INDEX IF NOT EXISTS idx_reading_session_paper
    ON reading_session (paper_id, started_at DESC);


-- ============================================================================
-- 表 4：annotation —— 批注与书签（RC 阶段用）
-- Alpha 阶段：**只建空表，不写入**
-- ============================================================================
CREATE TABLE IF NOT EXISTS annotation (
    id                BIGSERIAL    PRIMARY KEY,
    user_id           BIGINT       NOT NULL DEFAULT 1,
    paper_id          BIGINT       NOT NULL
                      REFERENCES papers(id) ON DELETE CASCADE,

    page              INT          NOT NULL CHECK (page >= 1),
    content           TEXT         NOT NULL,                 -- 批注内容
    color             VARCHAR(16)  NOT NULL DEFAULT 'yellow',-- 高亮颜色

    -- 批注位置：与 chunks 同坐标系（归一化 0~1），RC 阶段填充
    bbox_x0           DOUBLE PRECISION CHECK (bbox_x0 BETWEEN 0 AND 1),
    bbox_y0           DOUBLE PRECISION CHECK (bbox_y0 BETWEEN 0 AND 1),
    bbox_x1           DOUBLE PRECISION CHECK (bbox_x1 BETWEEN 0 AND 1),
    bbox_y1           DOUBLE PRECISION CHECK (bbox_y1 BETWEEN 0 AND 1),

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE annotation IS '批注与书签；Alpha 只建表不写入，RC 阶段实现';

CREATE INDEX IF NOT EXISTS idx_annotation_paper_page
    ON annotation (paper_id, page);


-- ============================================================================
-- updated_at 自动维护（papers / annotation 各一个触发器）
-- 避免每个人 UPDATE 时忘了写 updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_papers_updated_at ON papers;
CREATE TRIGGER trg_papers_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_annotation_updated_at ON annotation;
CREATE TRIGGER trg_annotation_updated_at
    BEFORE UPDATE ON annotation
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ============================================================================
-- P6 建表后的验收自查
-- ============================================================================
-- 1) 四张表都在
--    \dt
--
-- 2) pgvector 装了、维度对
--    SELECT extname FROM pg_extension WHERE extname = 'vector';
--    SELECT attname, atttypid::regtype FROM pg_attribute
--     WHERE attrelid = 'chunks'::regclass AND attname = 'embedding';
--
-- 3) 级联删除有效（插一条假数据再删论文）
--    INSERT INTO papers (title, filename, file_path) VALUES ('t','t.pdf','/tmp/t.pdf');
--    INSERT INTO chunks (paper_id, chunk_index, page, content)
--      VALUES (currval('papers_id_seq'), 0, 1, 'x');
--    DELETE FROM papers WHERE id = currval('papers_id_seq');
--    SELECT count(*) FROM chunks;   -- 应为 0
--
-- 4) 状态约束生效
--    UPDATE papers SET parse_status = 'done' WHERE id = 1;
--    -- 预期：violates check constraint "papers_parse_status_check"
