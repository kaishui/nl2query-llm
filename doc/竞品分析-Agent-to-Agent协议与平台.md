# Agent-to-Agent（A2A）：给 CTO 的决策简报

> **一句话结论**：A2A 的协议战已经结束，我们不需要赌协议；真正要在 90 天内定的是——**要不要给 NII 问数能力开一个对外接口，以及用谁的身份与网关来管它**。
> **建议**：开，但只开三个能力、最小改动、不绑任何一家云。投入约 60 人日，无新增采购。

---

## 0. 决策摘要（一页看完）

| # | 需要拍板的事 | 建议 | 代价 | 不做的后果 | 时间窗 |
|---|---|---|---|---|---|
| **D1** | NII 问数 agent 是否对外提供 A2A 接口 | **是**，只暴露 3 个 skill（查询/归因/临时取数），不改动 graph 内部结构 | 约 20 人日（P1） | 每接一个下游 agent 写一次点对点集成，第 4 个起维护成本失控 | 2 周内启动 |
| **D2** | 身份与网关归谁管 | **自建 agentgateway + 自持 Agent Card**，不绑单一云 | 0 采购，需网关团队 0.2 FTE | 绑定某家云后，身份映射与审计记录带不走 | 与 D1 同步 |
| **D3** | 是否建 agent 注册中心 | **不建**。先用 Git + 文件，12 个月后再评估 | 无 | 过早建 Registry 会变成新孤岛 + 影子 AI 的遮羞布 | 2027 H2 复盘 |
| **D4** | Agent Card 是否纳入变更管理 | **是**，等同模型变更（版本化、评估、可回滚） | 流程成本，约 2 人日/季度 | 模型换版导致对外行为漂移，监管视角属未申报变更 | 立即生效 |

**投入**：2 人 × 6 周（约 60 人日），复用现有 K8s 与 API 网关，**无新增软件采购**。
**回报**：下游 agent 接入从「每家 2-3 周定制」降到「读一张卡 + 配一次策略」；口径版本、审批留痕、调用审计三件事一次性收口。
**最大风险不是技术，是组织**：网关团队与安全团队谁对 agent 流量负责，必须在 D2 里一次定清，双头管理会直接拖死这个项目。

---

## 1. 现状总结：三句话

**第一句：协议层没有悬念了。**
A2A 于 2026-03 发布 v1.0（首个稳定版），2026-08 以 Growth Stage 项目并入 Linux Foundation 的 Agentic AI Foundation（AAIF），与 MCP、goose、AGENTS.md 同一治理体系。IBM 的竞争协议 ACP 已于 2025-08 归档并入。AWS、Azure、Google 三家云原生支持，Salesforce、ServiceNow、SAP 作为业务侧接入方。**这一层的选择风险已经归零——继续观望不会带来信息增量，只会推迟集成债的偿还。**

**第二句：平台层正在打，打的是「注册中心 + 身份」。**
三家云路线不同：Microsoft 押 Entra Agent ID（身份先行）、AWS 押治理面与发现面分离的 Agent Registry（2026-08-31 GA）、Google 押协议原生网关（能解析 MCP 方法名做 RBAC）。**它们都"支持 A2A"，但支持的是同一个协议、不同的控制面——这才是锁定风险的所在。**

**第三句：我们其实已经具备条件，只差一层壳。**
现有实现与 A2A 概念是天然映射的：

| 现有资产 | 对应 A2A 概念 | 价值 |
|---|---|---|
| `graph.py` 的 query / attribution / adhoc 三分支 | 三个 skill 写进一张 Agent Card | 分支即能力边界，不用重新设计接口 |
| `metrics.py` 指标字典 | skill 描述里的**口径契约**（版本 + 可用维度） | 这是我们相对通用 agent 的真壁垒 |
| `interrupt` 人工审批 | A2A `input-required` 状态 | 控制流不用改，审批天然成为协议的一部分 |
| `sql_guard.py` 只读校验 | 工具层（MCP）职责 | 不应上升到 A2A 层 |

**结论**：不需要重构，只需要在现有服务外面包一层，把「能力」和「口径」说清楚。

---

## 2. 为什么现在做，以及不做的代价

**做的理由（按重要性排序）**

1. **避免 N×N 集成**。行内已经有信贷、风控、财富、报表方向的 agent 在立项。每接一个下游就写一次定制适配，是典型的平方级成本；A2A 把它降成线性。
2. **口径治理收口**。现在「这个数怎么算的」靠人问人。A2A 的 Agent Card 强制我们把口径版本写进契约，等于把 `metrics.py` 的治理成果对外显性化。
3. **审批留痕可审计**。`interrupt` → `input-required` 的映射，让「谁委托、谁审批、批的什么」进入标准状态机，比自研日志更经得起检查。
4. **资产可携带**。Agent Card 是一张 JSON，换平台能带走；这决定了我们未来可以换云而不重写。

**不做的代价（12 个月内会显性化）**

- 每新增一个消费方，2-3 周定制开发，且各自实现一套权限校验，审计口径不统一。
- 口径版本散落在各团队文档里，出现「同一个 NII 两个数」时无法自证。
- 一年后被业务倒逼接入，届时只能照着某家云的方案赶工，失去议价权。

**但也要说清：现在大举投入同样是错的。** 拆微服务、建注册中心、绑一家云的托管方案，这三件事在任何情况下都不建议（理由见第 6 节风险表）。

---

## 3. 三个选项：成本、风险、可逆性

| | **A. 维持现状** | **B. 轻量出口（推荐）** | **C. 全面平台化** |
|---|---|---|---|
| **范围** | 不对外，只服务内部 | 三个 skill 对外 + 统一网关 | 建 Registry、拆多 agent、接托管平台 |
| **周期** | — | 6 周（P0 2 周 + P1 4 周） | 6-9 个月 |
| **人力** | 0 | 2 人 × 6 周 ≈ 60 人日 | 4-6 人 × 2 季度 |
| **现金投入** | 0 | **0**（复用 K8s + 现有网关） | 云托管按调用计费 + 网关改造，需商务询价 |
| **锁定风险** | 无（但也没资产） | **低**：协议资产自持，可平移 | **高**：Registry 策略与审计记录绑平台 |
| **可逆性** | — | 高（一层壳，可摘） | 低（拆分后难合回） |
| **失败模式** | 一年后被倒逼，被动赶工 | 网关团队不配合，卡在评审 | 半年后变成「两个控制面」，状态分裂 |
| **适合前提** | 确认 12 个月内无跨 agent 需求 | 有 1 个以上真实下游消费方 | 已有 10+ agent 且跨组织发现是刚需 |

**为什么推荐 B 而不是 C**：我们目前只有 1 个对外场景、0 个跨组织发现需求。C 方案的能力（注册中心、目录、联邦）在 10 个 agent 以下不会产生收益，但会立即产生运维负担和架构约束。**B 是「花 60 人日买一个随时可升级的期权」，C 是「在需求出现前先把自己焊死在一个平台上」。**

---

## 4. 推荐路径：90 天，两个阶段，一道闸门

### 阶段 P0：契约先行（2 周，不写业务代码）

| 交付物 | 验收标准 | 负责人 |
|---|---|---|
| `agent-card.json` 草稿 | 三个 skill；每个 skill 写明输入/输出模式、口径版本、**明确不支持什么** | 数据/指标 owner |
| 对外能力说明（1 页） | 另一个团队读完能判断「能不能问、问了会给什么」 | 产品 |
| 委托链与审计设计 | 每跳换发受众限定短时凭证；审计能还原「原始主体 → 委托链 → 动作」 | 安全架构 |

### 闸门 G1：安全评审（1 周）

**只有三个问题，答不上就不进 P1**：
1. A 委托 B 再调 C 时，C 拿到的是谁的权限？凭证怎么限定受众？
2. 出事时，能不能在 30 分钟内还原「谁委托、基于什么授权、谁批的」？
3. 租户（总行/分行/多法人）数据边界由谁强制，网关还是 agent？

### 阶段 P1：单点打通（4 周）

- 用 A2A Python SDK 在现有服务**外面**包一层 server，`graph.py` 一行不改。
- 起 agentgateway：JWT 鉴权 + 按 skill 粒度 RBAC + 审计日志。
- 打通一条完整链路：下游 agent 委托 → `input-required` → 人工审批 → 返回结果。
- **验收**：审计日志能回答 G1 的三个问题；下游接入耗时 < 1 天。

### 阶段 P2：治理化（6 周，可选，按需启动）

Agent Card 纳入 Git 版本管理 → 接 OTel 全链路 trace → 口径版本写入 task metadata → 建立季度协议一致性回归（防对方升级打破兼容）。

**关键设计原则**：A2A 只放在**边界**上。graph 内部 12 个节点不拆成 12 个 agent——那是把函数调用改成网络调用，延迟翻倍、trace 断裂、状态分裂，收益为零。

---

## 5. 成本与资源（诚实版）

| 项目 | 估算 | 说明 |
|---|---|---|
| **一次性人力** | 60 人日 | P0 20 + G1 5 + P1 35，2 人并行 6 周 |
| **持续性人力** | 0.2 FTE | 策略维护、协议升级回归、季度一致性测试 |
| **软件采购** | 0 | agentgateway 为 Apache 2.0；A2A SDK 开源 |
| **基础设施** | 可忽略 | 复用现有 K8s 与 API 网关；A2A 是纯 HTTP，不需要新网络域 |
| **审计存储** | 需评估 | 任务状态 + 委托链留痕，按现有日志留存策略估算，量级与 API 网关日志相当 |
| **组织成本（最大项）** | 网关团队 0.2 FTE + 安全评审 1 轮 | **这是最容易被低估、也最容易让项目停摆的一项** |

> 若未来选择云托管方案，成本模型会从「人力」转为「按调用量/运行时计费」，需商务介入询价；本报告不建议在当前阶段引入。

---

## 6. Top 5 风险登记表

| # | 风险 | 触发信号 | 影响 | 缓解 | Owner |
|---|---|---|---|---|---|
| R1 | **委托链裸转发 token**（confused deputy） | 代码里出现「把收到的 Authorization 直接透传给下游」 | 权限越界，且审计无法归因 | 每跳换发受众限定短时凭证；网关强制校验 audience | 安全架构 |
| R2 | **审计只能还原状态，还原不了业务语义** | 审计日志只有「调用了 NII agent」，没有口径版本 | 监管问询时无法自证 | 口径版本、数据截止日写入 Agent Card 与 task metadata | 数据 owner |
| R3 | **平台锁定** | Registry/策略成为唯一真相源，Agent Card 只存在平台上 | 换平台需重建治理体系 | Agent Card 与 skill schema 存自有 Git；平台只做分发 | 架构 |
| R4 | **对方版本落后** | 跨机构对接首次请求即 400（对方仍是 0.3） | 对接延期，商务关系受损 | Agent Card 同时声明多版本；上线前做版本协商测试 | 集成 |
| R5 | **把 A2A 当架构改造借口** | 出现「把 graph 节点拆成独立 agent」的提案 | 工期翻倍、性能下降、故障定位困难 | 在 D1 决议里写死边界：只在服务边界使用 | CTO |

**另有三个明确不做的事**（建议写进决议，避免反复讨论）：
1. 不为 A2A 拆微服务；
2. 现阶段不自建 agent 注册中心；
3. 现阶段不接 AP2（agent 支付），但审批记录结构预留可映射到 Mandate 的字段。

---

## 7. 需要 CTO 拍的四个决定

| # | 决定 | 建议 | 如果不拍 |
|---|---|---|---|
| **D1** | 批准 B 方案，投入 60 人日 | 批准 | 下游接入继续点对点，Q2 起维护成本线性上升 |
| **D2** | 明确 agent 流量的**唯一 owner**（网关团队 or 安全团队，二选一） | 网关团队 owning，安全团队定策略 | 双头管理，评审无限循环 |
| **D3** | 确认「不拆微服务、不建 Registry」的边界 | 确认 | 项目范围失控，6 周变 6 个月 |
| **D4** | Agent Card 纳入变更管理 | 确认 | 模型/prompt 变更未申报，监管风险 |

**建议的汇报节奏**：G1 闸门后一次安全评审结论汇报；P1 结束后一次演示（15 分钟，只看「委托→审批→返回→审计还原」这一条链）；此后按季度看四个观察指标。

---

## 8. 12 个月观察指标（用于复盘，不是用于宣传）

判断这步棋走对没走对，看四个可验证信号，不看新闻稿：

1. **A2A 是否落地合规元数据与可验证委托凭证** —— 决定银行能不能真用；若 12 个月内未落地，自建部分要加厚。
2. **AGNTCY 的目录是否出现真实跨机构部署**（而非厂商自述）—— 决定发现层要不要投入。
3. **AWS 的 ARD 联邦规范是否被微软/Google 采纳** —— 决定发现层会不会再分裂一次。
4. **各云厂商 A2A 实现是否通过一致性测试** —— 现在「支持 A2A」的定义太松，挂个 endpoint 也算。

**复盘时点**：2027 年 H1，与 D3（是否建 Registry）的决策合并评估。

---

## 附录 A：协议层矩阵（技术团队用）

| 协议/组件 | 层级 | 解决问题 | 治理 | 成熟度 | 与 A2A 关系 |
|---|---|---|---|---|---|
| **A2A** | 协作层 | agent 间发现、委托、长任务协作 | AAIF | 生产可用（v1.0.1） | 本体 |
| **MCP** | 工具层 | agent 接工具/数据/API | AAIF | 事实标准，10,000+ server | 互补（垂直） |
| **AGNTCY** | 基础设施层 | 目录（OASF/ADS）+ SLIM 安全传输（MLS） | Linux Foundation（Cisco 主导，65+ 公司） | 早期但在跑 | 互补，用 SLIM 承载 A2A 流量 |
| **ANP** | 发现/身份 | W3C DID/VC 去中心化身份 | 社区/研究 | 早期 | 可组合，缺桥接 |
| **AP2** | 支付 | 签名 Mandate 记录授权，agent 代付 | Google 发起，60+ 伙伴 | 早期 | A2A 扩展 |
| **x402** | 支付 | HTTP 402 + 稳定币按请求结算 | Coinbase 等 | 早期 | 正交 |
| **agentgateway** | 网关 | HTTP/gRPC/LLM/MCP/A2A 统一数据面，JWT+RBAC | AAIF（Rust, Apache 2.0） | 可用于生产 | A2A 的运维层 |

**同名陷阱**（评审时容易出错）：IBM 的 ACP（已并入 A2A）≠ AGNTCY 的 Agent Connect Protocol（活着）≠ Agentic Commerce Protocol（支付）≠ LangChain Agent Protocol（只是单 agent HTTP 服务）。

## 附录 B：平台层矩阵

| 平台 | A2A 角色 | 治理抓手 | 锁定风险 | 适配度 |
|---|---|---|---|---|
| **Microsoft Foundry + Copilot Studio** | 双向（调外部 + 暴露自身） | Entra Agent ID、条件访问 | 中（身份绑 Entra） | 高（若已用 Azure AD） |
| **AWS Bedrock AgentCore** | 托管 + 治理中枢 | Agent Registry 双平面（治理面/发现面分离）、IAM 级 RBAC、ARD 联邦 | 中低（框架无关） | 高（贴内控「先审批再暴露」） |
| **Google Vertex / Gemini Enterprise** | 原生 | Agent Gateway 协议级 RBAC（SPIFFE）、Model Armor | 中 | 中高（需 K8s+Envoy 底座） |
| **Salesforce / ServiceNow / SAP** | 消费方/编排方 | 各自 Trust Layer、Control Tower | 高（数据与流程绑定） | 中（单域场景） |
| **LangGraph Agent Server（自托管）** | 托管 + 消费 | 自建（配 agentgateway） | **低** | **高（代码零改造）** |

关键事实：LangGraph **库本身不说 A2A**（编译后的 graph 是对象，没有网络服务）；是 Agent Server（LangSmith Deployment，可自托管）把每个 assistant 暴露在 `/a2a/{assistant_id}` 并发布 Agent Card。所以我们不需要改动现有实现，只需要在部署形态上加一层。

## 附录 C：评分卡（5 分制，2026-11 快照，权重按强监管场景）

| 维度 | 权重 |
|---|---|
| 身份与信任 | 20% |
| 授权与数据边界 | 20% |
| 协议一致性与版本协商 | 15% |
| 审计与可追溯 | 15% |
| 可观测与成本归因 | 10% |
| 生态与互操作 | 10% |
| 锁定与退出成本 | 10% |

| 方案 | 加权得分 |
|---|---|
| Google Vertex + Agent Gateway | 4.55 |
| Microsoft Foundry + Entra Agent ID | 4.45 |
| AWS AgentCore + Agent Registry | 4.35 |
| A2A 1.0 + agentgateway（自建组合） | 4.30 |
| Salesforce / ServiceNow 原生 | 3.00 |
| 厂商私有协议（点对点） | 1.65 |

> 读法提醒：差值 0.2 以内不构成决策依据。Google 分高是因为网关层做得最彻底，但若底座不是 K8s + Envoy，该分数对我们无效——**分数反映能力，不反映适配**。

---

## 参考来源

- A2A 官方《A New Chapter for A2A: Joining the Agentic AI Foundation》(2026-08-27)：https://a2a-protocol.org/latest/blog/2026/08/27/a-new-chapter-for-a2a-joining-the-agentic-ai-foundation/
- Microsoft Learn《Connect to an A2A agent endpoint from Foundry Agent Service》：https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent
- Azure 博客《Ship agents faster…》（A2A GA、Routines GA）：https://azure.microsoft.com/en-us/blog/ship-agents-faster-with-expanded-model-choice-voice-agents-and-continuous-optimization/
- agentgateway 官方文档（AAIF 项目）：https://agentgateway.dev/docs/standalone/latest/documentation/about/introduction/
- Forbes《Agent2Agent Joins The Agentic AI Foundation Alongside MCP》(2026-08)：https://www.forbes.com/sites/janakirammsv/2026/08/19/agent2agent-joins-the-agentic-ai-foundation-alongside-mcp
- O-mega《MCP vs A2A in 2026》：https://o-mega.ai/articles/mcp-vs-a2a-in-2026-which-agent-protocol-to-use
- Dreaming Press《A2A vs ACP vs AGNTCY》：https://dreaming.press/posts/a2a-vs-acp-vs-agntcy-agent-interop-protocols.html
- David Prat《How enterprises are wiring AI in 2026》（LangGraph Agent Server A2A 端点）：https://www.davidprat.com/posts/how-enterprises-are-wiring-ai-2026
- Alice Labs《A2A Protocol Guide 2026》：https://alicelabs.ai/en/insights/a2a-protocol-guide-2026
