# NII 智能问数系统（显式 LangGraph 状态图）

基于 LangGraph + SQLite 的银行 NII 自然语言问数 / 归因分析 PoC。

## 架构

显式状态图（`app/graph.py`），每个环节都是可审计的节点：

```
                ┌────────── 校验失败带错误反馈重试（最多 2 次）──────────┐
                ↓                                                      │
用户问句 → 意图识别 → SQL 生成（受指标口径约束）→ SQL 校验 → 执行 + 归因 → 答案生成
                │                                        │
                ├─ query：受治理指标确定性取数              │
                ├─ attribution：归因三效应                 │
                └─ adhoc：opencode 动态生成 SQL（长尾兜底） │
                                                          │
                              高危查询（全表扫描 / 跨度 > 12 个月 / adhoc）
                              → interrupt 人工审批，批准后继续
```

三种意图分支：

- **query** — 受治理指标确定性取数（`metrics.py` 指标字典，LLM 不直写 SQL）
- **attribution** — NII 归因三效应（规模/价格/结构）
- **adhoc** — 受治理指标覆盖不了的长尾问题，走 opencode 动态生成 SQL，但执行前强制人工审批 + `sql_guard` 只读校验

相比 `create_agent` 黑盒（旧链路保留在 `app/agent.py`），显式状态图带来：

- **自纠错回路**：校验失败把错误原因回写给意图识别节点重新理解
- **human-in-the-loop**：高危 SQL 执行前 `interrupt` 等人工审批（金融合规刚需）
- **Checkpointer**：会话状态持久化，支持多轮追问与断点续跑
- **可观测**：每个节点的输入输出都在 state 中，可接 LangSmith 全链路 trace

## 目录结构

```
nl2query-llm/
├── app/
│   ├── db.py            # SQLite 数据初始化 + NII 模拟数据
│   ├── metrics.py       # NII 指标口径定义（受治理的指标字典）
│   ├── graph.py         # 显式 LangGraph 状态图（主链路，含 adhoc 分支）
│   ├── sql_guard.py     # SQL 安全校验 + 只读执行（白名单/注入拦截）
│   ├── opencode_sql.py  # opencode 动态 SQL 生成（adhoc 长尾兜底）
│   ├── agent.py         # 旧链路：create_agent 黑盒 + 受治理工具层
│   └── attribution.py   # NII 归因三效应计算
├── main.py              # CLI 入口（单问 / 多轮会话）
├── tests/
│   ├── test_smoke.py    # 冒烟测试：数据层 / 口径 / 归因（不依赖 LLM）
│   ├── test_graph.py    # 状态图测试：FakeLLM 驱动（不依赖 LLM）
│   ├── test_sql_guard.py# SQL 安全校验测试
│   └── test_adhoc.py    # opencode adhoc 分支测试（注入 fake nl2sql）
└── requirements.txt
```

## 运行

```bash
# 1. 安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置 LLM
export OPENAI_API_KEY=sk-xxx          # 走 OpenAI
export OPENAI_BASE_URL=...            # 可选，本地/其他 OpenAI 兼容接口
export OPENAI_MODEL=gpt-4o-mini       # 可选，默认 gpt-4o-mini

# 3. 单问单答
python main.py "Q3 NII 环比为什么下降了"

# 4. 多轮会话（同一 thread 共享记忆，可追问）
python main.py --chat

# 5. 运行测试（不依赖真实 LLM）
python tests/test_smoke.py
python tests/test_graph.py
python tests/test_sql_guard.py
python tests/test_adhoc.py
```

高危查询（不带时间条件的全表扫描、跨度超 12 个月、adhoc 自由取数）会暂停并提示人工审批，输入 `y` 批准、`n` 驳回。

### 启用 opencode 动态 SQL（可选）

```bash
pip install --pre opencode-ai
# 启动 opencode server（默认 127.0.0.1:4010）
export OPENCODE_BASE_URL=http://127.0.0.1:4010   # 可选
```

不装 opencode 也能跑——adhoc 分支会优雅降级返回错误，不影响 query/attribution 确定性路径。

高危查询（不带时间条件的全表扫描、跨度超 12 个月）会暂停并提示人工审批，输入 `y` 批准、`n` 驳回。

## 说明

- PoC 阶段用 SQLite 存模拟数据，生产可替换为 Postgres/ClickHouse；checkpointer 默认 MemorySaver，生产可换 SqliteSaver/PostgresSaver。
- SQL 由「SQL 生成节点」基于受治理的指标口径确定性拼装，LLM 只做意图识别和答案解读，不直写裸 SQL。
- SQL 校验节点：指标白名单、月份格式、起止顺序、跨度上限（24 个月）、维度取值白名单。
- 归因三效应：规模效应 / 价格效应 / 结构效应（结构效应用残差保证三项和精确等于 NII 增量）。
