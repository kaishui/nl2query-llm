# Spec 驱动开发（SDD）工具竞品分析

> 目标：以 **VS Code / IntelliJ IDEA 插件生态丰富度** 为核心维度，横向评估市面主流 Spec-Driven Development（SDD）工具（GitHub Spec Kit、OpenSpec、AWS Kiro、BMAD-METHOD 等），并给出对应的插件/工具链推荐。
> 核心结论先行：**SDD 工具本身几乎都不以「独立插件」形态出现，而是通过斜杠命令（slash command）+ AI 编码助手插件落地**。因此「选 SDD 工具」≈「选它背后能跑的 AI 助手插件生态」。

---

## 一、一个关键认知：SDD 工具 ≠ 插件，而是「命令层」

Spec Kit / OpenSpec 的本质是 **Markdown 规格文件 + 一组斜杠命令（slash command）+ CLI**，它们自己不渲染界面，而是把命令注入到 AI 编码助手里执行。

| 层 | 组成 | 举例 |
|---|---|---|
| **命令层（SDD 工具）** | 斜杠命令 + 规格模板 + 目录结构 | `/speckit:specify`、`/opsx:propose` |
| **执行层（AI 助手插件）** | 真正读规格、写代码的 Agent | Claude Code、Copilot、Junie、Codex |
| **承载层（编辑器）** | 插件跑在哪 | VS Code、IntelliJ IDEA、Cursor |

**所以真正的决策点是：你的团队用 VS Code 还是 IntelliJ IDEA？这个平台上哪个 AI 助手插件最成熟？SDD 工具对它的支持度如何？**

---

## 二、主流 SDD 工具插件生态对比（核心）

| 工具 | VS Code 支持 | IntelliJ IDEA 支持 | 独立插件 | 落地方式 |
|---|---|---|---|---|
| **GitHub Spec Kit** | ✅ 最强 | ✅ 强 | ❌（无自有插件） | `/speckit:*` 命令注入 30+ AI 助手（Claude Code、Copilot、Cursor、Junie、Codex、Gemini CLI、Windsurf、通义灵码、Kimi、Trae…） |
| **OpenSpec** | ✅ 强 | ✅ 中 | ✅ OpenSpec Workbench（VS Code 扩展，含 standalone 网页版） | `/opsx:*` 命令注入 Claude Code / Copilot / Codex / Gemini / Windsurf / OpenCode / Cursor；JetBrains 走 ACP |
| **AWS Kiro** | ✅ 原生（VS Code fork） | ⚠️ 弱（无原生插件，靠 ACP 接 JetBrains AI Assistant） | ✅ Kiro IDE（fork） | 独立 IDE，或 Kiro CLI + ACP |
| **BMAD-METHOD** | 🟡 中 | 🟡 中 | ❌ | 多 Agent 框架 + 斜杠命令，依赖外部 Agent 承载 |
| **Agent OS** | 🟡 中 | 🟡 中 | ❌ | 标准注入（advisory），Claude Code 调优为主 |
| **Tessl** | — | — | — | closed beta，平台/registry，暂不可生产 |

---

## 三、承载层：VS Code 与 IntelliJ 的 AI 助手插件现状

### VS Code（插件生态最成熟）

| AI 助手插件 | 说明 | SDD 兼容 |
|---|---|---|
| **Claude Code**（Anthropic 官方扩展） | 侧边栏面板、内联 diff、checkpoint 回滚、@提及；SDD 工具首推承载 | ✅ Spec Kit / OpenSpec 官方推荐 |
| **GitHub Copilot** | 微软官方，补全 + Chat + agent | ✅ Spec Kit 原生 / OpenSpec 支持 |
| **Cursor**（独立编辑器） | Composer 模式适合规格澄清迭代 | ✅ Spec Kit / OpenSpec 均支持 |
| **Codex**（OpenAI 扩展） | VS Code 官方扩展，需 `--ai-skills` | ✅ 两工具均支持 |
| **OpenCode / Roo Code / Cline** | 开源、BYOK、多模型 | ✅ OpenSpec 官方支持 |

### IntelliJ IDEA（JetBrains 生态）

| AI 助手插件 | 说明 | SDD 兼容 |
|---|---|---|
| **Junie**（JetBrains 官方） | JetBrains 自己的 agentic 层，IDE 原生 + 终端 + CI | ✅ Spec Kit 官方支持（`--ai-commands-dir` / generic） |
| **Claude Code**（Anthropic 官方插件） | 在 IDE 终端跑 `claude`，接 diff viewer、选择共享、诊断 | ✅ 官方支持 |
| **Codex**（JetBrains AI Chat 内建） | Read-only / Agent / Agent full access 三模式 | ✅ OpenSpec 支持 |
| **Kilo Code** | MIT 开源，v7 支持 IntelliJ/WebStorm/PyCharm/GoLand/Rider 等 | 🟡 通用 ACP |
| **OpenCode**（ACP） | MIT 终端 Agent，经 ACP 接入 JetBrains AI Chat | ✅ OpenSpec 支持 |
| **AWS Kiro**（ACP） | 经 JetBrains AI Assistant + ACP 接入（无原生插件） | ✅ 自身即 SDD |

> 关键点：IntelliJ 从 2025.2 起内置 **MCP Server**，外部客户端（Claude Code、Codex、Junie、Copilot CLI 等）可自动配置接入，这是 JetBrains 侧 SDD 工具链的底层通道。

---

## 四、核心对比维度

1. **插件形态** — 独立插件 vs 斜杠命令注入 vs 独立 IDE（fork）
2. **VS Code 覆盖度** — 能否直接在 VS Code 侧边栏/终端跑通全流程
3. **IntelliJ IDEA 覆盖度** — 是否原生插件，还是靠 ACP/MCP 间接接入
4. **AI 助手承载广度** — 支持多少个 AI 助手（Spec Kit 30+，OpenSpec 8+）
5. **多工具共存** — 团队成员各用各的编辑器能否统一流程（Spec Kit 强）
6. **独立 UI** — 有无 dashboard/workbench（OpenSpec Workbench 独有）
7. **锁定程度** — 是否绑定某云/某 IDE（Kiro 绑定 AWS，其余开源无锁定）
8. **规格强制力** — 规格是否「约束」代码（多数只是约定，会漂移）

---

## 五、重点竞品对比矩阵

| 维度 | GitHub Spec Kit | OpenSpec | AWS Kiro | BMAD-METHOD |
|---|---|---|---|---|
| **插件形态** | 命令层（无自有插件） | 命令层 + Workbench 扩展 | 独立 IDE（VS Code fork） | 命令层（无自有插件） |
| **VS Code** | ✅ 最强（30+ 助手） | ✅ 强（8+ 助手 + 自有扩展） | ✅ 原生（fork） | 🟡 中 |
| **IntelliJ IDEA** | ✅ 强（Junie/Claude/Codex） | 🟡 中（ACP） | ⚠️ 弱（ACP 间接） | 🟡 中 |
| **独立 UI/Dashboard** | ❌ | ✅ Workbench | ✅ IDE 内建 | ❌ |
| **AI 助手承载** | 30+（最多） | 8+ | 绑定 Kiro | 多 Agent 框架 |
| **多工具共存** | ✅ 最强 | ✅ | ❌ 单 IDE | 🟡 |
| **开源/锁定** | MIT 无锁定 | MIT 无锁定 | ❌ AWS 锁定 | MIT 无锁定 |
| **社区/生态** | ~14 万 star，GitHub 背书 | ~7 万 star | AWS 官方 | ~3.7 万 star |
| **上手成本** | 中（前期问询多） | 低 | 中（换 IDE） | 高 |

---

## 六、选型建议（按编辑器生态）

### 决策树

| 你的团队现状 | 推荐 SDD 工具 | 推荐承载插件 |
|---|---|---|
| **VS Code 为主** | OpenSpec 或 Spec Kit | Claude Code（首选）+ Copilot 共存 |
| **IntelliJ IDEA 为主** | **GitHub Spec Kit**（对 Junie/Claude 支持最全） | Junie（官方）+ Claude Code 插件 |
| **VS Code + IntelliJ 混用** | **GitHub Spec Kit**（多工具共存最强） | 各自原生助手，规格统一 |
| **深度 AWS 生态** | Kiro | Kiro IDE（VS Code 侧）/ CLI+ACP（JetBrains 侧） |
| **要独立 dashboard 监督 Agent** | OpenSpec + Workbench | Claude/Copilot/Codex/Gemini 任选 |

### 关键结论

1. **VS Code 团队选 OpenSpec**：插件生态最灵活（8+ 助手 + 自有 Workbench 扩展），上手最轻、漂移最低。
2. **IntelliJ IDEA 团队选 Spec Kit**：它对 JetBrains 生态（Junie、Claude Code 插件、Codex）的命令注入最完整，多工具共存能力是硬需求场景下的最优解。
3. **混编团队（最常见）选 Spec Kit**：30+ AI 助手统一接口，`--ai-commands-dir` 可让成员各用各的编辑器，规格资产仍共享一份。

---

## 七、推荐插件清单（可直接落地）

### VS Code 侧

| 插件 | 用途 | 安装 |
|---|---|---|
| **Claude Code** | SDD 首选承载 Agent，读 spec 写代码 | 扩展市场搜「Claude Code」 |
| **GitHub Copilot / Copilot Chat** | 补全 + agent，Spec Kit 原生集成 | 市场搜「GitHub Copilot」 |
| **OpenSpec Workbench** | OpenSpec 的 dashboard，监督/启动 Agent | openspec-ui.dev 下载 VSIX |
| **Codex**（可选） | 需要 `--ai-skills` 时用 | 市场搜「Codex」 |

### IntelliJ IDEA 侧

| 插件 | 用途 | 安装 |
|---|---|---|
| **Junie** | JetBrains 官方 agentic 层，SDD 承载 | 市场搜「Junie」 |
| **Claude Code**（Anthropic 官方） | 终端跑 claude + diff viewer | 市场搜「Claude Code」 |
| **Codex**（AI Chat 内建） | 三权限模式 agent | AI Chat 内选择 |
| **Kilo Code**（可选） | MIT 开源多模型 agent | 市场搜「Kilo Code」 |
| **OpenCode**（ACP） | 开源终端 Agent 接 AI Chat | 配 acp.json |

### CLI（两侧通用，规格资产核心）

- **Spec Kit CLI**：`uvx --from git+https://github.com/github/spec-kit.git specify init`
- **OpenSpec CLI**：`npm i -g @fission-ai/openspec` 或独立二进制
- **Kiro CLI**：`curl -fsSL https://cli.kiro.dev/install | bash`

---

## 八、下一步行动

- [ ] 确认团队主力编辑器（VS Code / IntelliJ 占比）
- [ ] 按第六节决策树选定 SDD 工具（倾向：混编选 Spec Kit，纯 VS Code 选 OpenSpec）
- [ ] 在对应编辑器装 1 个 AI 助手插件 + 1 个 SDD CLI，跑通一个 feature 的完整闭环
- [ ] 用 constitution / 全局规范沉淀研发约定，验证多编辑器规格一致性

---

## 参考来源

- GitHub Spec Kit: https://github.com/github/spec-kit（~14 万 star，30+ AI 助手集成）
- OpenSpec: https://github.com/Fission-AI/OpenSpec（openspec.dev）
- OpenSpec Workbench: https://openspec-ui.dev/（VS Code 扩展 + standalone）
- AWS Kiro: https://kiro.dev/（VS Code fork，JetBrains 走 ACP）
- JetBrains Junie / MCP Server: https://www.jetbrains.com/help/idea/mcp-server.html
- BMAD-METHOD: https://github.com/bmad-code-org/BMAD-METHOD
- SDD 工具横向对比: https://codemyspec.com/blog/best-spec-driven-development-tools
