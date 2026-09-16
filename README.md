# NII 智能问数系统（LangChain 底座）

基于 LangChain + SQLite 的银行 NII 自然语言问数 / 归因分析 PoC。

## 架构

```
用户问句 → 意图识别 → SQL 生成（受指标口径约束）→ 执行 → 归因解读
                 └── LangChain Agent（tool-calling）
```

## 目录结构

```
nl2query-llm/
├── app/
│   ├── db.py            # SQLite 数据初始化 + NII 模拟数据
│   ├── metrics.py       # NII 指标口径定义（受治理的指标字典）
│   ├── agent.py         # LangChain Agent 主链路
│   └── attribution.py   # NII 归因三效应计算
├── main.py              # CLI 入口
├── tests/
│   └── test_smoke.py    # 冒烟测试
└── requirements.txt
```

## 运行

```bash
# 1. 安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置 LLM（二选一）
export OPENAI_API_KEY=sk-xxx          # 走 OpenAI
export OPENAI_BASE_URL=...            # 可选，本地/其他 OpenAI 兼容接口
export OPENAI_MODEL=gpt-4o-mini       # 可选，默认 gpt-4o-mini

# 3. 初始化数据 + 运行
python main.py "Q3 NII 环比为什么下降了"

# 4. 运行冒烟测试（不依赖 LLM）
python tests/test_smoke.py
```

## 说明

- PoC 阶段用 SQLite 存模拟数据，生产可替换为 Postgres/ClickHouse。
- SQL 由工具层基于「受治理的指标口径」确定性拼装，LLM 不直写裸 SQL。
- 归因三效应：规模效应 / 价格效应 / 结构效应（结构效应用残差保证三项和精确等于 NII 增量）。
- 基于 langchain 1.x 的 `create_agent`（LangGraph 状态图）API。
