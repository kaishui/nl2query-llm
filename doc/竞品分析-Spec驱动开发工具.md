# Spec 驱动开发（SDD）工具竞品分析

> 目标：评估将 Spec-Driven Development（SDD）方法引入 NII NL2Query 产品研发流程的可行性，梳理市面主流 SDD 工具（GitHub Spec Kit、OpenSpec、AWS Kiro、BMAD-METHOD 等），给出对比维度与选型建议。
> 背景：本项目当前采用「LLM 不直写裸 SQL、SQL 由受治理指标口径确定性拼装」的核心设计原则——这与 SDD「意图即真相、规格即契约」的理念高度同构，值得系统性评估工具化落地。

---

## 一、什么是 Spec-Driven Development（SDD）

**先写规格（Spec），再写代码**，与传统的「先编码、后补文档」相反。

- **规格是契约**：定义代码应该如何行为，是 AI Agent 生成、测试、验证代码的**唯一事实来源（source of truth）**。
- **意图即真相**：GitHub 提出的范式转变——从「code is the source of truth」走向「intent is the source of truth」。
- **解决的核心问题**：vibe coding（氛围式编码）的上下文漂移、需求偏差、不可审计。语言模型擅长「模式补全」，不擅长「读心术」，规格把隐性意图显式化。

### 与本项目的契合点

| 本项目原则 | SDD 对应机制 |
|---|---|
| LLM 只做意图识别，SQL 由代码确定性拼装 | 规格约束 Agent 行为，Agent 不「自由发挥」 |
| 受治理指标口径（metrics.py） | 规格作为可验证的工程产物（而非一次性文档） |
| 高危 SQL 人工审批（human-in-the-loop） | 阶段检查点 + 人工 review 规格 |
| 显式状态图、可审计节点 | 变更可追踪、可版本化、可审计 |

---

## 二、竞品全景

| 类别 | 代表工具 | 本质 | 一句话定位 |
|---|---|---|---|
| **① 方法论 + CLI 工具包** | GitHub Spec Kit、OpenSpec | 规格先行的工作流，落成 CLI + slash 命令 | 把「写清楚再动手」固化成流程 |
| **② 集成式 Agentic IDE** | AWS Kiro | 把 SDD 做成 IDE 一等公民 | 换 IDE 换来的端到端集成 |
| **③ 多 Agent 团队模拟** | BMAD-METHOD | 模拟完整敏捷团队产出 PRD/架构/故事 | 最重的仪式感，最全的纸面留痕 |
| **④ 轻量标准注入** | Agent OS | 在既有代码上注入团队规范（advisory） | 让 Agent 不再对抗你的 house rules |
| **⑤ 规格即平台（前瞻）** | Tessl（closed beta） | 以 spec-as-source 为核心建平台 | 观察项，尚不可生产使用 |
| **⑥ 语言/框架绑定 BDD 门禁** | CodeMySpec | Phoenix/Elixir，强制 BDD 门禁 + QA Agent | 垂直场景的强制验证 |

---

## 三、核心对比维度

### A. 工作流与产物

1. **阶段划分** — 几阶段？Spec Kit 是四阶段（specify→plan→tasks→implement），OpenSpec 是「变更增量」模型（change→artifacts→implement→archive）。
2. **规格格式** — 结构化 Markdown（OpenSpec 用 SHALL/MUST + WHEN/THEN 场景）vs 自由散文。
3. **变更管理模型** — 全量重写 vs 增量（ADDED/MODIFIED/REMOVED/RENAMED，OpenSpec 类似数据库迁移）。
4. **宪法/规范继承** — 项目级规则集是否被每个 spec 自动继承（Spec Kit 的 constitution 是核心）。

### B. 强制力与验证（关键分水岭）

5. **规格是否「约束」代码** — 多数工具只是「生成 spec 然后甩给另一个 Agent」，规格不被强制执行的只是「文档」，文档会漂移。
6. **验证门禁** — 有无内置 verify（OpenSpec 的 validate 是结构化检查，非阻塞；CodeMySpec 是强制 BDD 门禁）。
7. **spec drift 治理** — 规格漂移谁来管（多靠人工）。

### C. 工程化与集成

8. **Agent 兼容性** — 支持多少个 AI 编码助手（Spec Kit ~30 个，OpenSpec 多工具，Kiro 绑定自家 IDE）。
9. **安装/分发** — 独立二进制（OpenSpec 8 平台）vs uv/Python（Spec Kit）vs Node。
10. **安全与可复现** — 构建溯源、HTTPS 强制、路径逃逸防护、字节级可复现打包（Spec Kit 的 bundler 极强）。
11. **锁定程度** — 是否绑定单一平台/云（Kiro 绑定 AWS Bedrock，Spec Kit/OpenSpec 均为 MIT 开源无锁定）。

---

## 四、重点竞品对比矩阵

| 维度 | GitHub Spec Kit | OpenSpec | AWS Kiro | BMAD-METHOD | Agent OS | Tessl |
|---|---|---|---|---|---|---|
| **定位** | Agent 无关的 SDD 默认选择 | 轻量 brownfield 增量规格 | 集成式 Agentic IDE | 多 Agent 团队模拟 | 既有代码标准注入 | 规格即平台（前瞻） |
| **开源/许可** | ✅ MIT | ✅ MIT | ❌ 商业（Bedrock 计量） | ✅ MIT | ✅ MIT | ❌ closed beta |
| **工作流** | specify→plan→tasks→implement 四阶段 | change→增量→archive | 需求/设计/任务三产物同步 | PRD→架构→故事分片 | 规范注入（advisory） | n/a |
| **规格格式** | 结构化 Markdown | SHALL/MUST + WHEN/THEN 场景 | EARS 式验收准则 | 超详细故事文件 | 团队规范 | n/a |
| **变更模型** | 按 feature 全量 | 增量 ADDED/MODIFIED/REMOVED | 三产物同步 | PRD + stories | 无持久 spec | n/a |
| **宪法/规范继承** | ✅ 核心特性 | 🟡 较弱 | 🟡 | 🟡 | ✅（就是做这个） | n/a |
| **强制力/门禁** | 约定（无强制） | validate 结构检查（非阻塞） | review-gated（不强制） | 流程 gate（handoff） | advisory only | 平台级 |
| **Agent 兼容** | ✅ ~30 个 | ✅ 多工具 | ❌ 绑定 Kiro IDE | ✅ 多工具 | 🟡 Claude Code 调优 | n/a |
| **安装/分发** | uv + Python | 独立二进制（8 平台） | IDE 安装 | Node/agents | CLI | n/a |
| **安全/可复现** | ✅ 强（bundler） | ✅ 强（签名溯源） | 🟡 | 🟡 | 🟡 | n/a |
| **greenfield 新项目** | ✅ 优 | 🟡 | ✅ 优 | ✅ 优（重） | ❌ 不适合 | — |
| **brownfield 存量改造** | 🟡 | ✅ 优 | 🟡 | ❌ 摩擦大 | ✅ 优 | — |
| **上手成本** | 中（前期问询多） | 低 | 中（需换 IDE） | 高（学习曲线） | 低 | — |
| **Token 成本** | 高（spec 占 34%） | 低（spec 占 28%） | 中 | 高（spec 占 44%） | 低 | — |

---

## 五、第三方实测数据（Uvik SDD Benchmark 2026 Q4）

50 个生产级 Python ticket 上四工具 vs 无规格对照（来源：uvik.net）：

| 指标 | Spec Kit | Kiro | BMAD | OpenSpec | 无规格对照 |
|---|---|---|---|---|---|
| **Merge rate（/50）** | 80% | 82% | 82% | **84%** | 72% |
| **单 ticket 成本（USD）** | $3.33 | $2.35 | $4.23 | **$2.71** | $2.43 |
| **Spec 漂移率** | 12.5% | 4.9% | 12.2% | **2.4%** | n/a |
| **每 ticket 返工轮次** | 0.62 | 0.64 | 0.46 | 0.52 | 0.74 |
| **规格完整性（/8）** | 6 | 7 | 7 | 7 | 0 |
| **工程师复用意愿** | 4/5 | 4/5 | 3/5 | **5/5** | n/a |

### 关键结论

- **规格在「3 个文件以上」的 ticket 上才回本**：小 ticket（1-2 文件）规格成本 > 它避免的返工；中型（3-5 文件）规格臂 85% vs 对照 70%；大型（6+ 文件）80% vs 50%。
- **规格收益集中在 feature 和 data-pipeline 类 ticket**（+30pp），bug-fix / refactor 类几乎零收益（0pp）。
- **OpenSpec 漂移率最低（2.4%）、复用意愿最高（5/5）**，性价比突出。

---

## 六、选型建议

### 规则总纲

> **写规格先行，review 的是规格而非 diff，让意图而非氛围驱动 Agent。**

### 按场景匹配（决策树）

| 场景 | 推荐 | 理由 |
|---|---|---|
| 新项目、要严谨、跨技术栈 | **GitHub Spec Kit** | 社区最大、Agent 支持最广、constitution 规范继承 |
| 存量代码持续演进、要轻 | **OpenSpec** | 增量模型专为 brownfield、上手快、漂移低 |
| 深度 AWS 生态 | Kiro | 集成体验好，但锁定 Bedrock、计量收费 |
| 复杂绿地产品、要纸面留痕 | BMAD-METHOD | 全流程团队模拟 + 合规证据，但最重、最贵 |
| 只想让 Agent 遵守现有规范 | Agent OS | 标准注入，不做持久 spec |
| Phoenix/Elixir 强验证 | CodeMySpec | 强制 BDD 门禁 |

### 对本项目（NII NL2Query）的落地建议

1. **选型倾向：OpenSpec 为主、Spec Kit 为辅。** 本项目是「存量代码 + 受治理口径 + human-in-the-loop」的成熟 PoC，恰好命中 OpenSpec 的强项（brownfield 增量、漂移低、轻量）。Spec Kit 的 constitution 可用于沉淀全局规范（如「LLM 不直写裸 SQL」）。

2. **优先对「大 ticket」上规格。** 结合 benchmark 结论，对涉及 `app/graph.py`、`metrics.py`、`opencode_sql.py` 多文件联动的改动先写 spec；单文件小修不强行上规格。

3. **把「受治理口径」翻译成 spec 的强制约束。** 用 SHALL/MUST 表达「SQL 必须由 metrics.py 确定性拼装、LLM 不得直写裸 SQL」「高危 SQL 必须 interrupt 人工审批」，让规格成为合规证据链的一部分。

4. **先试点后推广。** 挑一个 feature（如 adhoc 分支的 sql_guard 增强）跑通 OpenSpec 的 change→archive 闭环，验证增量模型与现有 LangGraph 状态图的可审计性是否契合，再决定是否全量铺开。

---

## 七、下一步行动

- [ ] 安装 OpenSpec，在 `doc/` 旁建 `openspec/` 目录跑通首个 change 闭环
- [ ] 用 constitution（Spec Kit 概念）沉淀 3-5 条全局研发规范
- [ ] 选定 1 个多文件 feature 做 SDD 试点，量化 merge rate / 返工轮次
- [ ] 评估「受治理指标口径」与 spec 强制约束的映射，形成合规证据链

---

## 参考来源

- GitHub Spec Kit: https://github.com/github/spec-kit
- GitHub 官方 SDD 博客: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- OpenSpec: https://github.com/Fission-AI/OpenSpec（openspec.dev）
- AWS Kiro: https://kiro.dev/
- BMAD-METHOD: https://github.com/bmad-code-org/BMAD-METHOD
- Uvik SDD Benchmark 2026 Q4: https://uvik.net/spec-driven-development-benchmark
- SDD 工具横向对比: https://codemyspec.com/blog/best-spec-driven-development-tools
