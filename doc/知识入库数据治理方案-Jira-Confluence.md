# Jira + Confluence 知识入库数据治理方案

> 文档日期：2026-11-07
> 项目定位：银行 Treasury 企业级 LLM Wiki 的第一阶段接入（Jira + Confluence）
> 关联仓库：github.com:kaishui/nl2query-llm
> 前置文档：`doc/竞品分析-企业级LLM-Wiki银行Treasury.md`

---

## 一、范围与目标

本方案聚焦两个系统的知识接入：**Confluence（文档知识库）** 与 **Jira（工单/任务/缺陷）**，回答四个问题：

1. 哪些数据进 pgvector（语义检索层），哪些进关系表（元数据层），哪些不落库（实时连接）
2. PG 表结构如何设计（含 ACL 权限内嵌）
3. 同步策略（全量初始化 + 增量更新 + 过期治理）
4. 权限与安全（银行场景硬性要求）

> **核心判据（贯穿全文）**：这条数据是「要被语义搜到的内容」→ 进向量；还是「用来过滤/关联的事实」→ 进关系表；还是「随时会变的状态」→ 不落库，实时连。

---

## 二、数据分流清单

### 2.1 Confluence

| 数据 | 去向 | 说明 |
|------|------|------|
| 页面正文（架构、SOP、制度、设计稿） | ✅ vector | 核心语义检索对象 |
| 页面标题、空间(space)、父页面、标签 | ✅ 关系表 | 层级导航 + 过滤 |
| 附件 PDF/图片文字（解析后） | ✅ vector | 需版面解析 / OCR |
| 页面版本历史 | ❌ 实时连接 | 需要时走 Confluence API |
| 评论、点赞、@提及、实时编辑 | ❌ 实时连接 | 高频变动，存副本必过期 |

### 2.2 Jira

| 数据 | 去向 | 说明 |
|------|------|------|
| issue 描述 + 复现步骤 + 解决方案 | ✅ vector | 找相似 bug、沉淀方案 |
| issue 标题 | ✅ vector（轻量，随描述一起） | 检索召回入口 |
| 状态、优先级、组件、版本、经办人、sprint | ✅ 关系表 | 过滤聚合（"P0 未关闭"） |
| 附件截图文字（OCR） | ✅ vector | 有排查价值 |
| epic / link 依赖关系 | ✅ 关系表 | 依赖图 |
| 工作流流转、评论、通知、审计轨迹 | ❌ 实时连接 | 留原系统，避免过期副本 |

---

## 三、PG 表结构设计

采用「正文 + 向量 + 元数据 + ACL 同库一体」的设计，权限在检索 SQL 层内嵌过滤，而非应用层事后遮罩。

### 3.1 核心表：`knowledge_chunks`（向量 + 正文）

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source        text NOT NULL CHECK (source IN ('confluence', 'jira')),
  source_id     text NOT NULL,           -- 原系统主键：confluence page_id / jira issue_key
  chunk_index   int  NOT NULL DEFAULT 0, -- 同一文档的第几个分块
  title         text,                    -- 页面标题 / issue 标题
  content       text NOT NULL,           -- chunk 正文（检索与生成都用它）
  embedding     vector(1536),            -- embedding 维度按模型定（OpenAI text-embedding-3-small=1536）
  metadata      jsonb NOT NULL DEFAULT '{}', -- 结构化元数据（见 3.2）
  owner_id      text,                    -- 知识所有者（account id）
  allowed_groups text[] NOT NULL DEFAULT '{}', -- ACL：可见组/空间/项目
  content_hash  text,                    -- 内容指纹，用于增量判断是否变化
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source, source_id, chunk_index)
);

CREATE INDEX idx_chunks_embedding ON knowledge_chunks
  USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_source ON knowledge_chunks (source, source_id);
CREATE INDEX idx_chunks_groups ON knowledge_chunks USING gin (allowed_groups);
```

### 3.2 元数据表：`source_metadata`（关系表，结构化事实）

```sql
CREATE TABLE source_metadata (
  source      text NOT NULL,
  source_id   text NOT NULL,
  status      text,      -- jira: 状态/优先级/经办人/组件/sprint
  priority    text,
  assignee    text,
  components  text[],
  sprint      text,
  space_key   text,      -- confluence: 空间
  parent_id   text,      -- 父页面 / epic
  labels      text[],
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source, source_id)
);
```

> 检索查询示例（权限内嵌 + 元数据过滤 + 语义召回一体）：
> ```sql
> SELECT source, source_id, title, content, metadata
> FROM knowledge_chunks
> WHERE source = 'jira'
>   AND allowed_groups && ARRAY['treasury-team']   -- ACL 内嵌过滤
>   AND metadata->>'status' <> 'Closed'            -- 元数据过滤
> ORDER BY embedding <=> $query_vector             -- 语义召回
> LIMIT 10;
> ```

### 3.3 同步状态表：`sync_state`（增量游标）

```sql
CREATE TABLE sync_state (
  source        text PRIMARY KEY,
  last_synced_at timestamptz NOT NULL,
  cursor        text,          -- 增量游标（Jira 用 updated 时间 / Confluence 用 cursor）
  total_chunks  int
);
```

---

## 四、同步策略

### 4.1 全量初始化（首轮）

1. 拉取全量对象清单（Confluence 空间下所有页面 + Jira 项目下所有 issue）
2. 按「正文 + 元数据」分离：正文 → chunk → embedding 入库；元数据 → `source_metadata`
3. 记录 `content_hash`，作为后续增量判断基线

### 4.2 增量更新（定时任务）

| 触发方式 | 说明 |
|---------|------|
| Confluence | Webhook（页面创建/更新/删除事件）或定时轮询 CQL 按 `lastModified` 过滤 |
| Jira | Webhook（issue updated/deleted）或定时轮询 JQL 按 `updated >=` 过滤 |
| 变化检测 | 对比 `content_hash`，未变则跳过（省 embedding 成本） |
| 删除 | 源对象删除 → 软删除对应 chunk（标记 `deleted_at` 或直接删） |

### 4.3 新鲜度治理（银行合规刚需）

- 每条 chunk 记录 `updated_at`，超期未更新的「制度/口径类」文档进入待复核队列
- 知识所有者（`owner_id`）定期复核，未复核内容降低检索权重或下架
- 审计日志记录：谁在何时同步了哪条、变更了什么

---

## 五、权限与安全（银行 Treasury 场景强化）

1. **ACL 检索内嵌**：`allowed_groups` 在 SQL 层用 `&&` 过滤，检索前即按权限收窄，杜绝检索到无权限内容再事后遮罩
2. **空间/项目级隔离**：Confluence 按 space 权限、Jira 按 project 权限，映射为 `allowed_groups`；跨空间/跨项目内容默认不可见
3. **数据不出域**：embedding 模型与向量库均私有化部署，源数据脱敏后再入库
4. **审计可回源**：每条 chunk 带 `source + source_id`，任何 AI 答案可一键回源到 Confluence 页面 / Jira issue，形成证据链
5. **高风险拦截**：涉及资金头寸、监管口径、投资建议的检索结果，触发人工审批（复用 nl2query-llm 的 `interrupt` 机制）

---

## 六、与 nl2query-llm 的衔接

| 层 | nl2query-llm | 本方案（LLM Wiki 接入层） |
|----|--------------|--------------------------|
| 定位 | 问数（受治理指标 + 确定性 SQL） | 问知识（文档/工单语义检索） |
| 共享 | 指标口径字典、ACL 体系、interrupt 审批 | 复用同一套口径与权限 |
| 编排 | LangGraph 状态图 | 同一 LangGraph，新增「知识检索」节点 |

> 用户在统一入口提问时，LangGraph 先做意图路由：指标类问题 → nl2query 受治理取数；知识/文档类问题 → 本方案 pgvector 检索 + 引用回源；两者结果可合并回答。

---

## 七、落地步骤（第一阶段）

1. **建库建表**：初始化 PG + pgvector，执行第三节 SQL
2. **Confluence 接入**：全量拉取 treasury 空间页面 → 解析正文 → 分块 → embedding → 入库 + ACL 映射
3. **Jira 接入**：全量拉取资金条线项目 issue → 描述/方案入库 + 状态元数据入库
4. **增量同步**：配置 Webhook + 定时任务，验证新增/更新/删除链路
5. **检索验证**：构造 treasury 领域问题集，评估召回质量（准确率/引用回源正确率）
6. **接入 LangGraph**：新增知识检索节点，与 nl2query 意图路由打通
