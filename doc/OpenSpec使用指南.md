# OpenSpec 使用指南

> 本文档介绍如何在本仓库（nl2query-llm）中使用 [OpenSpec](https://openspec.dev) 进行规范驱动开发（Spec-Driven Development）。
> 关联文档：`doc/竞品分析-Spec驱动开发工具.md`（选型结论：OpenSpec 漂移率最低，适合 brownfield 增量）

---

## 一、为什么用 OpenSpec

OpenSpec 是一个轻量、brownfield-first 的规范驱动开发框架，核心价值：

1. **Spec 活在代码库里**：功能需求作为「活的文档」随代码一起版本化，新成员或 AI agent 可直接阅读 `openspec/specs/` 理解系统「应该做什么」，而非只看「现在做了什么」。
2. **先审意图、再审代码**：每次变更产出 spec delta（需求增删改的 diff），评审者无需深挖代码即可快速理解变更意图。
3. **跨会话持久**：规划不随聊天结束而消失，适合多轮、跨 agent 协作。
4. **与本项目契合**：nl2query-llm 强调「受治理指标口径 + human-in-the-loop」，OpenSpec 的 `proposal → apply → archive` 闭环正好承载这种「先规划、再实施、可审计」的流程。

---

## 二、安装与初始化

### 2.1 安装 CLI

```bash
# 推荐：独立二进制（无需 Node.js）
openspec install

# 或通过 npm
npm install -g @fission-ai/openspec
```

验证：

```bash
openspec version
```

### 2.2 初始化本项目

```bash
cd nl2query-llm
openspec init
```

`init` 会交互式询问使用哪些 AI 工具（Claude Code、Cursor、Codex 等），并写入对应的 workflow 文件。也可跳过交互：

```bash
openspec init --tools claude        # 指定工具
openspec init --tools none          # 仅创建 openspec/ 结构，不装工具文件
```

初始化后生成的结构：

```
openspec/
├── config.yaml          # 项目设置与上下文（替代旧版 project.md）
├── specs/               # 你的规范（初始为空）
└── changes/             # 进行中的变更
    └── archive/         # 已完成的变更归档
```

> 若有旧版 `openspec/project.md`，`init` 不会自动删除，会提示用 AI 迁移其内容到 `config.yaml`。

---

## 三、核心概念

| 概念 | 说明 |
|------|------|
| **Spec** | 描述系统某一能力的功能需求，位于 `openspec/specs/<capability>/spec.md` |
| **Change** | 一次待实施的变更，包含 `proposal.md` / `design.md` / `tasks.md` / spec delta |
| **Spec Delta** | 变更对既有 spec 的增删改（`ADDED` / `MODIFIED` / `REMOVED`） |
| **Archive** | 变更完成后移入归档，其 delta 合并进正式 specs |

---

## 四、工作流（三阶段闭环）

```
 想法 → propose（生成规划文档）→ 评审 → apply（实施）→ verify（验证）→ archive（归档合并）
```

### 阶段 1：Propose（提案）

需求明确后，一条命令生成全套规划文档：

```bash
# Claude Code 斜杠命令
/opsx:propose 为 NII 归因增加「结构效应」的可选下钻维度

# 等价 CLI（agent 自动调用）
openspec new add-attribution-structure-drilldown
```

产物（`openspec/changes/<change-id>/`）：

```
openspec/changes/add-attribution-structure-drilldown/
├── proposal.md   # 变更描述（Why / What Changes / Impact）
├── design.md     # 技术决策（Context / Decision / Consequences）
├── tasks.md      # 拆解的实施任务清单
└── specs/        # spec delta
    └── attribution/
        └── spec.md
```

**评审要点**：先读 `proposal.md` 和 spec delta，确认需求理解一致后再动手，把偏差消灭在写码之前。

### 阶段 2：Apply（实施）

规划确认后按 `tasks.md` 逐项实施：

```bash
/opsx:apply add-attribution-structure-drilldown
```

agent 会读取 spec 上下文，按任务顺序写代码，并在 `tasks.md` 中勾选完成项。

### 阶段 3：Verify 与 Archive（验证与归档）

```bash
# 验证实现是否符合 spec
/opsx:verify add-attribution-structure-drilldown

# 功能上线后归档：delta 合并进 specs/，变更移入 archive/
/opsx:archive add-attribution-structure-drilldown
```

归档后，正式规范更新到 `openspec/specs/attribution/spec.md`，成为系统的「活文档」。

---

## 五、常用命令速查

### 终端 CLI

| 命令 | 用途 |
|------|------|
| `openspec init` | 初始化项目 |
| `openspec list` | 查看进行中的变更 |
| `openspec list --specs` | 查看已归档规范 |
| `openspec show <id>` | 查看某变更/规范详情（markdown 或 JSON） |
| `openspec validate <id>` | 校验变更/规范结构 |
| `openspec validate --all` | 校验全部 |
| `openspec archive <id> --yes` | 归档（跳过确认） |
| `openspec view` | 终端一屏总览 specs 与 changes |
| `openspec update` | 更新已安装的 AI 指令文件 |
| `openspec config` | 查看/修改全局配置 |
| `openspec doctor` | 检查 OpenSpec root 关系健康度 |

### 对话斜杠命令（以 Claude Code 为例）

| 命令 | 触发节点 | 产物 |
|------|---------|------|
| `/opsx:explore` | 想法模糊，先讨论方案 | 仅对话，AI 分析代码库给建议 |
| `/opsx:propose` | 需求明确，准备开工 | proposal + specs + design + tasks |
| `/opsx:new` | 手动逐步创建 | 仅空变更目录 |
| `/opsx:continue` | 已有变更，补全缺失文档 | 逐个生成缺失 artifact |
| `/opsx:apply` | 规划确认后 | 按 tasks.md 写代码 |
| `/opsx:verify` | apply 完成后 | 验证报告 |
| `/opsx:archive` | 功能上线后 | 归档并更新 specs |

---

## 六、Spec 编写规范

### 6.1 需求关键词（强度由强到弱）

| 关键词 | 含义 |
|--------|------|
| `MUST` | 必须（最强） |
| `SHALL` | 应当（强） |
| `SHOULD` | 建议 |
| `MAY` | 可选 |

### 6.2 场景（Scenario）关键词

```markdown
#### Scenario: 默认会话超时
- GIVEN 用户已认证
- WHEN 24 小时无活动
- THEN 使会话 token 失效
- AND 要求重新认证
```

### 6.3 完整 Spec 模板

```markdown
# attribution Specification

## Purpose
管理 NII 归因的规模/价格/结构三效应计算。

## Requirements

### Requirement: 结构效应下钻
系统 SHALL 支持结构效应按产品维度下钻。

#### Scenario: 按产品下钻
- GIVEN 归因结果为结构效应
- WHEN 用户指定产品维度
- THEN 返回各产品的结构效应贡献
- AND 总和等于整体结构效应
```

### 6.4 Spec Delta 区段

| 区段 | 用途 |
|------|------|
| `## ADDED Requirements` | 新增能力 |
| `## MODIFIED Requirements` | 修改已有需求（须含更新后的完整文本） |
| `## REMOVED Requirements` | 移除/废弃需求 |

### 6.5 命名约定

- 变更目录：kebab-case，如 `add-attribution-structure-drilldown`
- Spec 目录：kebab-case，与能力名一致
- Markdown 文件：小写 + `.md`

---

## 七、在本项目中的实践建议

结合 nl2query-llm 的「受治理口径 + human-in-the-loop」架构，建议：

1. **先为现有核心能力补 spec**：优先为 `app/metrics.py`（指标口径）、`app/graph.py`（状态图意图路由）建立 spec，把「LLM 不直写 SQL」等治理原则固化为 `MUST` 级需求。
2. **新功能一律走 propose**：任何涉及指标口径、SQL 生成、审批流的改动，先 `/opsx:propose` 出 spec delta，评审通过再 apply——与现有的 `interrupt` 人工审批形成双重保险。
3. **高风险变更额外留痕**：涉及资金口径的 change，在 `proposal.md` 的 Impact 里明确标注合规影响，归档时保留证据链。
4. **spec 与文档分工**：`openspec/specs/` 承载「功能应该做什么」（可被 agent 读取的活规范），`doc/` 承载「调研/方案/竞品」等人类阅读的分析文档，二者不混用。

---

## 八、常见问题

**Q：OpenSpec 和我 agent 自带的 plan mode 有什么区别？**
Plan mode 只在单次聊天会话内有效；OpenSpec 的规划跨多个会话、可分享、贯穿整个开发生命周期。

**Q：能在已有代码库上用吗？**
可以。不必一次性补全所有 spec，按需创建、边做边补即可，这正是 brownfield-first 的设计。

**Q：切换 AI 工具时怎么办？**
Spec 存在仓库里，工具无关。在新工具上跑 `openspec init --tools <新工具>` 即可安装对应 workflow 文件。

---

## 参考

- 官方文档：https://openspec.dev/docs
- CLI 参考：https://openspec.dev/docs/cli
- 本项目竞品分析：`doc/竞品分析-Spec驱动开发工具.md`
