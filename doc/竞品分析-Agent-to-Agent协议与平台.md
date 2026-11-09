# Agent-to-Agent（A2A）竞品分析：协议层、平台层与银行落地选择

> **分析对象**：Agent 与 Agent 之间「发现—委托—协作」这条链路上的标准与产品（截至 2026-11 公开信息）。
> **核心结论先行**：A2A 在「协作层」已经赢了——2026-03 发布 v1.0、2026-08 并入 Linux Foundation 的 Agentic AI Foundation（AAIF），与 MCP 同一治理体系，AWS/Azure/Google 三家云原生支持，Salesforce/ServiceNow/SAP 作为业务侧接入方。
> **但真正的竞争不在协议，而在它上下两层**：往下是「工具层」MCP 已无可争（真正要决策的是怎么接），往上是「发现与身份层」至今没有赢家（AGNTCY、ANP、各家 Registry 正在打）。
> **对银行的含义**：A2A 解决的是「跨团队/跨厂商 agent 能不能通话」，**不解决**「通话时谁有权访问什么、出了问题谁负责、审计记录长什么样」。后三件事必须自建，且这正是选型时被厂商演示掩盖的部分。

---

## 一、先把问题定义清楚：A2A 在竞争什么

把「agent to agent」当成一个产品去找竞品，会找错对象。它其实是一个**三层栈**，每层的竞争格局完全不同：

| 层 | 解决什么问题 | 事实标准 | 竞争状态 |
|---|---|---|---|
| **工具层（垂直）** | 一个 agent 怎么用自己的工具、数据、API | **MCP** | 已定局，10,000+ server，所有主流模型厂商原生支持 |
| **协作层（水平）** | 一个 agent 怎么把任务委托给另一个 agent | **A2A** | 已定局，v1.0 + AAIF + 三大云原生支持 |
| **发现与身份层** | 两个互不认识的 agent 怎么找到对方、怎么信任对方 | **无** | **真正的战场**：AGNTCY / ANP / AWS Agent Registry / 各家 Agent 身份体系 |
| 支付层 | agent 之间怎么付钱 | AP2（A2A 扩展）、x402 | 早期多强并存 |
| 界面层 | agent 怎么把中间过程给人看 | AG-UI、A2UI | 早期，工具链配套 |

**一句话选型原则**：MCP 是必选项，A2A 是条件项（只在你真的有两个「不同 owner」的 agent 时才需要），发现层是观察项（现在押注会锁死）。

> 判断标准很硬：如果两个 agent 在同一个代码库、同一个部署、同一个团队维护，那根本不是 agent-to-agent 问题，是函数调用问题。硬上 A2A 只会换来延迟、token 开销和一堆序列化 bug。

---

## 二、标准之争：A2A 是怎么赢下协作层的

### 2.1 关键时间线（决定竞争格局的六个节点）

| 时间 | 事件 | 竞争含义 |
|---|---|---|
| 2025-04 | Google 发布 A2A，50+ 合作伙伴 | 抢在「事实标准」形成前占位，姿态是开放而非独家 |
| 2025-06-23 | Google 把规范、SDK、工具链捐给 Linux Foundation | **最关键一步**：把「Google 的协议」变成「行业的协议」，消解厂商锁定质疑 |
| 2025-08-27 | IBM 归档 ACP（Agent Communication Protocol），并入 A2A | 协作层唯一的正经对手退出，REST 简洁性被吸收进 A2A |
| 2025-09-16 | Google 发布 AP2（Agent Payments Protocol），60+ 支付/金融机构 | 从「能通话」扩到「能交易」，把金融业拉进生态 |
| 2025-12-09 | AAIF 成立（Anthropic、Block、OpenAI 共同发起；AWS、Google、Microsoft、Cloudflare、Bloomberg 支持），首批项目 MCP、goose、AGENTS.md | 把 MCP 也放进中立基金会，两层标准统一治理 |
| 2026-03-12 | **A2A v1.0 正式发布**（首个稳定版） | 从「能 demo」到「能进生产」的分水岭 |
| 2026-08-17/27 | A2A 以 Growth Stage 项目身份加入 AAIF，与 MCP、goose、AGENTS.md、agentgateway 并列 | 治理收敛完成，企业采购的最大异议（「会不会被单一厂商绑架」）被消掉 |

一周年（2026-04-09）时的公开数据：150+ 支持组织、GitHub 22,000+ star、SDK 覆盖 Python/JS/Java/Go/.NET 五种语言；到 2026-10 底 star 过 26,000，SDK 增至六种（含 Rust）。技术 steering committee 席位：AWS、Cisco、Google、IBM Research、Microsoft、Salesforce、SAP、ServiceNow——**没有单一厂商能否决线格式**。

### 2.2 v1.0 到底补了什么（企业敢用的真正原因）

| 能力 | v1.0 之前 | v1.0 之后 | 对银行的意义 |
|---|---|---|---|
| **Agent Card 签名** | 自述式 JSON，谁都能伪造 | JWS（RFC 7515）+ JCS 规范化（RFC 8785），可验证「这张卡确实来自它声称的域」 | 供应链 agent 冒名是真实攻击面，签名卡是底线 |
| **协议绑定** | JSON-RPC 为主 | JSON-RPC 2.0 / gRPC / HTTP+JSON 三绑定等价，`a2a.proto` 为规范源 | 行内 gRPC 体系不必为接 A2A 另起一套网关 |
| **多租户** | 无 | 请求级 `tenant` 字段 | 总行-分行、多法人场景必需 |
| **版本协商** | 升级即破坏 | 每接口独立版本，Agent Card 可同时声明 v0.3/v1.0 | 跨机构对接时对方版本落后不至于中断 |
| **OAuth 2.0 现代化** | 含 password/implicit 流 | 弃用不安全流，加 Device Code（RFC 8628）、PKCE 必选标记 | 过合规评审时少一个必改项 |
| **任务生命周期** | 有 | 保持 submitted → working → input-required → completed/failed/canceled 状态机，且状态可审计 | 长任务（报表跑批、审批流）可恢复、可追溯 |
| **Web 对齐架构** | 特殊网络要求 | 纯 HTTP 流量，负载均衡、WAF、私有端点、API 网关全部照常用 | 不需要为 agent 流量新开网络域，这一条对银行网络架构团队价值最大 |

**这就是 A2A 赢的真正原因**：不是设计更优雅，而是它把自己做成了「不需要新基础设施」的协议，同时把企业采购最在意的四件事（身份可验证、多租户、向后兼容、可审计状态）在 1.0 一次性补齐。

### 2.3 它仍然没解决的（也就是你要自建的部分）

1. **授权策略不标准化**：A2A 只规定「server 必须做授权检查并把结果限定在调用方权限内」，但策略模型故意留空。跨机构委托时，对方 agent 能碰什么，仍然落在你身上。
2. **委托凭证不可验证传递**：A 授权 B 访问数据，B 能否再授权 C？规范层面没有可验证的委托凭证（delegation token），生产上大量在裸转发 bearer token——这是 confused deputy 攻击的温床。
3. **能力描述 ≠ 能力等价**：「能查 NII」这张卡不说明口径版本、数据截止日、是否含税。语义互操作仍是人的工作。
4. **计费与结算**：AP2 在补，但银行间清结算的合规路径远未成型。
5. **合规元数据**：路线图上有（Agent Card 声明监管属性），但截至 2026-11 未落地。

---

## 三、协议层竞品矩阵

| 协议/组件 | 层级 | 解决的问题 | 治理 | 成熟度 | 与 A2A 关系 | 适用场景 | 风险 |
|---|---|---|---|---|---|---|---|
| **A2A** | 协作层 | agent 间发现、委托、长任务协作 | AAIF（Linux Foundation） | 生产可用（v1.0.1） | 本体 | 跨团队/跨厂商/跨机构 agent 互通 | 授权策略自建；实现深度参差 |
| **MCP** | 工具层 | agent 接工具、数据、API | AAIF | 生产可用（事实标准） | 互补，垂直/水平 | 所有 agent 的工具接入 | 工具投毒；scope 粒度粗 |
| **AGNTCY** | 基础设施层 | 目录（OASF schema + ADS）、Agent Connect Protocol、SLIM 安全传输（MLS 加密） | Linux Foundation（Cisco 主导，65+ 公司） | 早期但真在跑 | **互补，不是替代**；用 SLIM 承载 A2A/MCP 流量 | 跨组织发现、身份 schema 统一、需要硬化传输 | 组件多、学习曲线陡；任务模型弱 |
| **ANP** | 发现/身份层 | 基于 W3C DID/VC 的去中心化身份与开放网络 | 社区/研究主导 | 早期 | 可组合，缺现成桥接 | 开放互联网级 agent 身份 | 工程化远，Task 非一等公民 |
| **Coral Protocol** | 协作 + 支付 | MCP 原生 + 持久线程 + Solana 钱包身份 | 社区 | 小众 | 同类替代 | 加密原生场景 | 多模态弱，安全仅覆盖支付路径 |
| **AP2** | 支付层 | 签名 Mandate 记录用户授权，agent 代付 | Google 发起，60+ 伙伴 | 早期 | A2A 扩展（也可配 MCP） | agentic commerce、代客支付 | 银行清结算合规路径未定 |
| **x402** | 支付层 | 复活 HTTP 402，按请求用稳定币结算 | Coinbase 等 | 早期 | 与 A2A 正交 | 机器微支付 | 加密货币合规风险 |
| **agentgateway** | 网关/控制面 | HTTP/gRPC/LLM/MCP/A2A 统一数据面，JWT+RBAC、工具联邦、协议升降级 | AAIF（Rust，Apache 2.0） | 可用于生产 | A2A 的运维层 | 把 agent 流量纳入现有网关治理 | 需与 API 网关团队共建 |
| **AG-UI / A2UI** | 界面层 | agent 中间态/生成式 UI 的人机呈现 | 社区 | 早期 | 配套 | 前端可观测与交互 | 标准未稳 |

### 3.1 逐个短评（只写会影响决策的）

**AGNTCY —— 唯一有分量的「互补型竞争者」**
它回答的不是「agent 之间说什么」，而是「怎么找到、怎么信任、怎么安全路由」。用 HTTP 类比：A2A 是 HTTP，AGNTCY 是 DNS + TLS + 服务发现。它自己的仓库里有把 A2A/MCP 流量隧道化到 SLIM 的适配器，所以「A2A 还是 AGNTCY」是伪命题。**真正要判断的是：你有没有跨组织发现问题**——没有就别上，有就绕不开。

**ANP —— 路线不同，不必现在跟**
DID/VC 那套身份体系在理念上比签名 Agent Card 更彻底（去中心化、可验证凭证），但工程化和生态都远。它的价值是提示你：**Agent Card 的签名只解决「卡是谁发的」，不解决「这个 agent 有没有资格代表那家机构」**。后者最终要靠可验证凭证或行业准入名单，银行应当关注，但不必现在实现。

**ACP（IBM）—— 已死，但教训要记住**
REST 简洁、任务模型设计优秀，却在安全授权上几乎空白，最终归档并入 A2A。这是本轮标准之争最清晰的一课：**协议竞争不是比谁设计漂亮，是比谁先补齐企业采购清单**。

**AP2 / x402 —— 现在只需观察，但要留接口**
AP2 的「签名 Mandate」思路对银行极有价值：它把「用户授权」变成不可否认的记录，正好对应内部授权审批留痕。如果你的 agent 未来要代客操作资金/交易，AP2 的 Mandate 模型比任何一家厂商的私有方案都更接近监管语言。

**注意三个同名陷阱**（连专业文章都会写错）：
- IBM 的 **ACP**（Agent Communication Protocol）已并入 A2A ≠ Cisco AGNTCY 里的 **Agent Connect Protocol**（还活着）
- **Agentic Commerce Protocol** 是支付标准，与上面两个都无关
- LangChain 的 **Agent Protocol** 只是「把单个 agent 暴露成 HTTP 服务」的 API（runs/threads），**不是**跨 agent 互操作标准

---

## 四、平台层竞品矩阵（真正的采购决策发生在这里）

协议是免费的，钱花在平台上。平台层的竞争焦点已经从「支持不支持 A2A」变成「**谁做 agent 的注册中心、身份与策略中枢**」。

| 平台 | A2A 角色 | A2A 版本/形态 | 注册与发现 | 身份与策略 | 可观测/审计 | 锁定风险 | 银行适配度 |
|---|---|---|---|---|---|---|---|
| **Microsoft Foundry + Copilot Studio** | **双向**（调外部 + 自己暴露为 endpoint） | A2A 工具 **GA（1.0）**；`a2a_preview`（0.3）保留 | Foundry 项目内 A2A connection + Agent Card | Entra Agent ID、条件访问、集中凭据与策略 | OTel + Foundry 追踪/评估；Agent 365 注册表 | 中（身份绑 Entra） | 高（若已用 Azure + AD） |
| **AWS Bedrock AgentCore** | **托管 + 治理中枢** | 原生 A2A hosting；Agent Registry GA（2026-08-31） | **Registry 双平面**：治理面存记录/策略，发现面只暴露已审批项；语义+关键词混合检索 | AgentCore Identity/Policy、IAM 级 RBAC；ARD 开放规范（Apache 2.0）做跨云联邦 | AgentCore Observability + CloudWatch，含成本归因 | 中低（框架无关，任意框架可跑） | 高（治理面/发现面分离 ≈ 行内「先审批再暴露」） |
| **Google Vertex AI Agent Builder / Gemini Enterprise** | 原生（发源地） | 原生 A2A hosting + 客户端 SDK；Marketplace **上架必须有 Agent Card** | Agent Card + Gemini Enterprise 私有市场 | IAM + **Agent Gateway**（Envoy/K8s Gateway API，解析 MCP 方法名与 A2A agent 身份，SPIFFE + RBAC）；Model Armor 防注入 | Agent Identity 密码学 ID + Security Command Center | 中 | 中高（网关级策略最接近银行需求） |
| **Salesforce Agentforce** | 消费方 + 暴露方 | Agentforce 3 起支持 A2A + MCP | AgentExchange 市场 | Einstein Trust Layer、审计轨迹、数据边界 | 平台内审计 | **高**（数据在 Salesforce） | 中（CRM 场景） |
| **ServiceNow** | 编排方 | AI Agent Orchestrator + AI Agent Fabric，基于 A2A/MCP | ServiceNow Store | AI Control Tower、工作流内人工审批 | 强（ITSM 原生审计） | 中高 | 高（IT/运维/工单场景） |
| **SAP (Joule)** | 编排 + 委托 | 用 A2A 把任务委派给 S/4HANA 生态伙伴 agent | 生态伙伴目录 | 平台权限 | 平台内 | 高（ERP 深度绑定） | 中（财务/采购域） |
| **Atlassian** | 工具方 + 协作 | MCP Server GA（220+ 工具）、发布 AMP（Agentic Multiplayer Protocol） | 自有 | 管理端沙箱 | 中 | 中 | 中（研发协作） |
| **LangGraph / LangSmith Deployment** | 托管 + 消费 | **Agent Server 直接提供 `/a2a/{assistant_id}` 并发布 Agent Card** | 每 assistant 一张卡 | 自建（配 agentgateway） | LangSmith 全链路 trace | **低**（可自托管） | **高**（可私有化 + 现有代码零改造） |
| **CrewAI / Pydantic AI / AG2 / LlamaIndex / ADK / MAF** | 库级支持 | 各有多 Agent 原语 + A2A 适配包 | 需自建 | 需自建 | 各不同 | 低 | 中（适合自研团队） |
| **kagent（CNCF）/ Agent Stack（LF，原 BeeAI）** | 运行时 + 网关 | 把任意框架 agent 包成 A2A server | K8s CRD / SDK | 依赖集群 | OTel + 持久任务（Postgres） | 低 | 中（kagent API 仍 v1alpha3，2026-10 文档标注多副本网关协调未实现） |

### 4.1 三条路线，三种哲学（这是全文最该记住的对比）

**路线 A：Microsoft —— 「身份先行」**
A2A 在 Foundry 里是一个**工具类型**（`a2a` GA / `a2a_preview` 旧版），同时可以把 Foundry agent 反向暴露成 A2A endpoint（Build 2026 预览）。它的护城河不在协议，在 **Entra Agent ID**：每个 agent 是一个有密码学身份、可被条件访问策略约束的主体。Microsoft Agent Framework 1.0（2026-04-03，Python/.NET 同日 GA）在 .NET 侧 4-28、Python 侧 7-30 补齐 A2A v1 支持，分 client（`A2ACardResolver`）与 hosting（`AddA2AServer` + `MapWellKnownAgentCard`）两个包。
→ **适合**：已经在 Entra ID 体系里做权限治理的机构。**代价**：agent 身份与目录强绑微软。

**路线 B：AWS —— 「治理平面与发现平面分离」**
Agent Registry（2026-08-31 GA，5 个月前才预览）最值得抄的不是技术，是**架构决策**：治理面存全部注册记录与策略，发现面**只向消费者暴露已通过审批的记录**。这正好对应银行「先审批、再暴露」的内控逻辑。同时它用 Apache 2.0 的 ARD 规范做跨云/本地/SaaS 联邦，避免 Registry 变成新孤岛。
→ **适合**：多框架、多 runtime 混跑，且需要「影子 AI」治理的机构。**代价**：平台团队要接受 AgentCore 作为 agent 运行时的中心。

**路线 C：Google —— 「协议原生网关」**
Google 在 Cloud Next '26 预览的 Agent Gateway（Envoy + K8s Gateway API）能做一件传统网关做不到的事：**解析 MCP 方法名与 A2A agent 身份，在协议层做 RBAC**，并用 SPIFFE 在 mTLS 握手时校验 agent 身份。示例场景是「只允许某 agent 调用特定 GitHub MCP 工具」。配合 Model Armor（防提示注入/工具投毒）与 Agent Identity（密码学 ID）。
→ **适合**：把「agent 流量治理」当成网络层问题解，而不是应用层问题解。**代价**：需要 Gateway API 为标准的 K8s 底座。

### 4.2 框架与运行时：一个容易踩的双控制面陷阱

LangGraph 的定位要说清楚：**库本身不说 A2A**（编译后的 graph 是个 Python 对象，没有网络服务）；是 **LangGraph Agent Server（LangSmith Deployment，可自托管）** 把每个 assistant 暴露在 `/a2a/{assistant_id}` 并发布 Agent Card。

上 A2A 有四条路：① 跑在 Agent Server 上；② 自己容器里用 A2A SDK 包一层；③ 跑在 kagent 下；④ 用 Agent Stack SDK 包。**对单个 supervisor graph，①② 就够**。

⚠️ **kagent 与 Agent Stack 不要同时上**：两者都要接管 agent 生命周期、注册表和状态，同时跑等于一个层两个控制面，agent 状态会分裂在 kagent 的 Postgres 和 LangGraph 的 checkpointer 两处。

---

## 五、评估维度与评分卡（按银行权重）

维度定义与权重（权重来自「强监管 + 多法人 + 已有 API 网关体系」这一前提，可按机构调整）：

| 维度 | 权重 | 说明 |
|---|---|---|
| 协议一致性与版本协商 | 15% | 实现的是 1.0 还是 0.3？三绑定支持几个？与旧客户端协商能力 |
| 身份与信任 | 20% | 签名卡是否强制校验？密钥归属如何证明？是否支持 SPIFFE/mTLS/委托凭证 |
| 授权与数据边界 | 20% | 策略在网关还是应用？能否按工具/方法级限权？多租户隔离 |
| 审计与可追溯 | 15% | 任务状态机是否留痕？能否还原「谁委托谁、基于什么授权」 |
| 可观测与成本归因 | 10% | OTel 覆盖度、按 agent/租户的 token 与时长归因 |
| 生态与互操作 | 10% | 对 A2A/MCP 之外（AGNTCY、AP2）的兼容姿态 |
| 锁定与退出成本 | 10% | 能否自托管？协议资产（Agent Card）能否带走 |

评分（5 分制，2026-11 快照）：

| 方案 | 协议一致性 | 身份信任 | 授权边界 | 审计 | 可观测 | 生态 | 锁定 | 加权 |
|---|---|---|---|---|---|---|---|---|
| A2A 1.0 + agentgateway（自建组合） | 5 | 4 | 4 | 4 | 4 | 4 | 5 | **4.30** |
| Microsoft Foundry + Entra Agent ID | 5 | 5 | 4 | 4 | 5 | 4 | 3 | **4.45** |
| AWS AgentCore + Agent Registry | 4 | 4 | 5 | 4 | 5 | 4 | 4 | **4.35** |
| Google Vertex + Agent Gateway | 5 | 5 | 5 | 4 | 4 | 4 | 3 | **4.55** |
| Salesforce / ServiceNow 原生 | 3 | 3 | 3 | 4 | 3 | 3 | 2 | **3.00** |
| 厂商私有协议（点对点集成） | 1 | 2 | 2 | 2 | 2 | 1 | 1 | **1.65** |

> 读法提醒：分数差 0.2 以内不构成决策依据，真正的差异在**你能不能用起来**——身份体系是否已有、网关团队是否愿意接、数据能不能出域。Google 分高是因为它在网关层做得最彻底，但如果你的底座不是 K8s + Envoy，这个分数对你无效。

---

## 六、银行场景的五个硬约束（竞品分析里最常被跳过的一节）

厂商演示永远展示「A 调 B 成功返回」，但银行评审会问的是下面五个问题。

**1）委托授权不可传递**
A 的 token 传给 B，B 再拿去调 C，出了事谁负责？A2A 规范要求 server 做授权检查并限定在调用方权限内，但**不提供可验证的委托凭证**。生产上普遍在裸转发 token，这是 confused deputy 的经典入口。
→ 自建：委托链上每一跳都换发**受众限定（audience-restricted）**的短时凭证，并在审计里记录「原始主体 → 委托链 → 最终动作」。

**2）审计要能还原「为什么」**
A2A 的任务状态机（submitted/working/input-required/completed）天然可审计，但它记录的是**状态**，不是**业务语义**。「这个数为什么这么算」不在协议里。
→ 自建：把指标口径版本、数据截止日、模型版本写进 Agent Card 的 skill 描述与任务 metadata，否则审计只能看到「调用了 NII agent」而看不到「用的哪版口径」。

**3）数据边界与多租户**
v1.0 的 `tenant` 字段解决了「请求属于哪个租户」，不解决「租户数据能不能被跨租户 agent 读到」。行内多法人、总分行场景尤其危险。
→ 自建：租户隔离放在网关 + 数据层，不依赖 agent 自觉。

**4）Agent 变更管理**
模型换版、prompt 改动、工具增删，都会改变 agent 行为。这在监管视角下等同于模型变更，需要版本化、评估、回滚。
→ 自建：Agent Card 带版本、变更留 diff、`agent-framework` 类框架的 checkpoint 要能回滚到上一版行为。Microsoft 的 declarative YAML agent 配置、AWS 的 Registry 版本记录，都是为这件事准备的。

**5）供应商锁定与退出**
Agent Card 是可带走的资产（一张 JSON），但**注册中心里的策略、身份映射、审计记录带不走**。
→ 自建：Agent Card 与 skill schema 存在自己的 Git 仓库（就像本项目的 `doc/` 与 `app/metrics.py`），平台只做分发不做唯一真相源。

**一句话**：A2A 把「通话」标准化了，但把「通话的合规性」留给了你。这既是风险，也是行内平台团队的价值所在。

---

## 七、对本项目（NII NL2Query）的启示

### 7.1 现状映射：你其实已经具备 A2A 化的条件

| 现有实现 | A2A 对应物 | 说明 |
|---|---|---|
| `app/graph.py` 的 query / attribution / adhoc 三分支 | **三个 skill** 写进一张 Agent Card | 分支即能力边界，天然适合对外描述 |
| `app/metrics.py` 指标字典 | skill 描述里的**口径契约**（版本 + 可用维度） | 这是你相对通用 agent 的真正壁垒 |
| `interrupt` 人工审批 | A2A `input-required` 状态 + 审批回调 | 状态机天生匹配，不用改造控制流 |
| `sql_guard.py` 只读校验 | **工具层**（MCP server 或内部工具） | 不要上升为 A2A 层职责 |
| LangGraph checkpointer | 任务持久化 + 断点续跑 | 与 A2A 长任务语义对齐 |

### 7.2 建议目标架构（最小改动版）

```
                        ┌──────────────────────────────┐
   信贷 agent ──A2A──▶  │  agentgateway（策略/审计）    │
   风控 agent ──A2A──▶  │  · JWT + RBAC（按 skill 限权）│
   财富 agent ──A2A──▶  │  · 签名 Agent Card 校验       │
                        └──────────────┬───────────────┘
                                       │ A2A 1.0（JSON-RPC）
                        ┌──────────────▼───────────────┐
                        │  NII 问数 Agent（LangGraph）  │
                        │  Agent Card:                 │
                        │   skill: nii_query           │
                        │   skill: nii_attribution     │
                        │   skill: nii_adhoc（需审批）  │
                        └──────┬───────────────┬───────┘
                               │ MCP           │ interrupt
                        ┌──────▼──────┐  ┌─────▼──────────┐
                        │ 指标/数据工具 │  │ 人工审批（合规）│
                        │ (metrics.db) │  └────────────────┘
                        └─────────────┘
```

要点：
- **A2A 只在边界上**：行内其他 agent 与本 agent 之间用 A2A；graph 内部 12 个节点**不要**拆成 12 个 agent。
- **MCP 做工具**：`metrics` / `db` / `sql_guard` 包成 MCP 工具，调用方无需知道内部口径实现。
- **审批不能省**：adhoc 分支的 `interrupt` 保留，A2A 层表现为 `input-required`，对外承诺「高危查询需人工放行」——这在银行是卖点不是缺点。

### 7.3 三阶段路线

| 阶段 | 时间 | 动作 | 验收标准 |
|---|---|---|---|
| **P0 内部对齐** | 2 周 | 手写一张 `agent-card.json`（三个 skill + 口径版本 + 认证方式）；把 `graph.py` 的三分支整理成对外契约文档 | 卡能被 A2A 客户端解析；skill 描述能让另一个团队看懂「能问什么、不能问什么」 |
| **P1 单点打通** | 1 个月 | 用 A2A Python SDK 在现有服务外包一层 server（不动 graph）；起一个 agentgateway 做 JWT + 按 skill 限权 | 另一个 agent 能完成一次「委托 → input-required → 审批 → 返回」全链路，且审计能还原委托链 |
| **P2 治理化** | 2-3 个月 | Agent Card 纳入 Git 版本管理；接 OTel；把口径版本写进 task metadata；评估接 AGNTCY 目录的必要性 | 能回答「上周三这个数是谁委托查的、用的哪版口径、谁批的」 |

### 7.4 明确不建议做的事

1. **不要为了 A2A 拆微服务**：graph 内节点改网络调用，延迟翻倍、trace 断裂、状态分裂。
2. **不要自建 agent 注册中心**：先用文件 + Git，等有 10 个以上 agent 再谈 Registry（届时优先评估 AWS Agent Registry 的双平面设计）。
3. **不要现在接 AP2**：除非要做代客交易；但把「审批记录」设计成可映射到 Mandate 的结构，留好出口。
4. **不要把 Agent Card 当营销页**：卡里写不清「不支持什么」，下游 agent 就会误调用，最后坏的是你的 SLO。

---

## 八、选型建议（决策树）

| 你的处境 | 建议 | 理由 |
|---|---|---|
| 只有一个 agent，工具也不多 | **只上 MCP，不上 A2A** | 没有第二个 owner 的 agent，A2A 纯开销 |
| 多团队各自有 agent，需互相调用 | **A2A 1.0 + MCP + 统一网关** | 标准已定，网关是你唯一能控制策略的地方 |
| 已有 Azure/Entra 体系 | Foundry（双向 A2A）+ Entra Agent ID | 身份复用，评审成本最低 |
| 多框架混跑、要治影子 AI | AWS AgentCore + Agent Registry | 治理面/发现面分离，最贴内控语言 |
| K8s + Envoy 底座、要协议级限权 | Google Agent Gateway 或 agentgateway | 能按 MCP 方法名/A2A agent 身份做 RBAC |
| 需要跨机构发现 | A2A + 观察 AGNTCY（OASF/ADS/SLIM） | 发现层无赢家，别单押 |
| 强监管、要私有化 | **LangGraph Agent Server（自托管）+ agentgateway** | 代码零改造、可自托管、协议资产自持 |
| 涉及代客支付 | 观察 AP2，接口抽象出 Mandate | 唯一在往监管语言靠的支付方案 |

**给本项目的结论**：走最后第二行——自托管 LangGraph Agent Server + agentgateway，A2A 只暴露三个 skill，MCP 承接工具层，审批留在图里。这条路改动最小、锁定最低，且随时可以平移到任何一家云的 A2A 托管服务（因为资产是 Agent Card 和 graph，不是平台 SDK）。

---

## 九、风险与反模式

**六个反模式**（按踩坑频率排序）：
1. **把内部函数调用包装成 A2A**：延迟 +300ms、调试成本翻倍，收益为零。
2. **只做「能调通」不做「能限权」**：demo 通过、评审不过。
3. **信任 Agent Card 的自述**：不验签的卡等于名片，谁都能印。
4. **忽略版本协商**：对方还是 0.3，你的 1.0 直接 400，跨机构对接第一次就翻车。
5. **注册中心当唯一真相源**：策略与审计被平台绑死，退出时资产归零。
6. **双控制面**：kagent + Agent Stack 同跑，agent 状态分裂，故障排查地狱。

**未来 12 个月值得盯的四个可验证信号**（不是新闻稿）：
- A2A 是否落地**合规元数据**（Agent Card 声明监管属性）与**可验证委托凭证**——这决定银行能不能真用。
- AGNTCY 的 ADS 目录是否出现真实的跨机构部署（而非厂商自述）。
- AWS Agent Registry 的 **ARD 联邦规范**是否被微软/Google 采纳——决定发现层会不会再分裂一次。
- 各云厂商 A2A 实现是否通过一致性测试（现在「支持 A2A」的定义太松：挂个 endpoint 也算）。

---

## 十、结论（五条）

1. **协作层没有竞争了**。A2A v1.0 + AAIF 治理 + 三大云原生支持 + IBM ACP 并入，这一层再选私有协议是纯粹的技术债。
2. **工具层更没有竞争**。MCP 是必选项，问题只是「接哪些工具、scope 怎么划」。
3. **真正的竞争在发现与身份层，且没有赢家**。AGNTCY（去中心化目录 + 安全传输）、ANP（DID/VC）、各家 Registry（中心化治理）三条路线并行，现在押注就是赌。**用 A2A 的卡，别锁 Registry 的实现**。
4. **平台层的差异不在协议支持，在身份与策略**。Microsoft 押 Entra Agent ID、AWS 押治理面/发现面分离、Google 押协议原生网关——这三条都能用，选哪条取决于你现有的身份底座和网关团队，而不是 benchmark。
5. **A2A 把「通话」标准化，把「合规」留给你**。对银行来说，后者才是工程量的 80%：委托凭证、审计语义、租户隔离、变更管理、退出路径。**这五项自建能力，才是竞品分析真正的产出**。

---

## 参考来源

- A2A 官方博客《A New Chapter for A2A: Joining the Agentic AI Foundation》(2026-08-27)：https://a2a-protocol.org/latest/blog/2026/08/27/a-new-chapter-for-a2a-joining-the-agentic-ai-foundation/
- A2A 规范与 v1.0 迁移说明：https://a2a-protocol.org/
- Microsoft Learn《Connect to an A2A agent endpoint from Foundry Agent Service》（A2A 1.0 GA / 0.3 preview）：https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent
- Microsoft Learn《Enable incoming A2A on a Foundry agent》：https://learn.microsoft.com/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint
- Azure 博客《Ship agents faster with expanded model choice, voice agents, and continuous optimization》（A2A GA、Routines GA、Toolboxes）：https://azure.microsoft.com/en-us/blog/ship-agents-faster-with-expanded-model-choice-voice-agents-and-continuous-optimization/
- agentgateway 官方文档（AAIF 项目，统一 HTTP/gRPC/MCP/A2A 数据面）：https://agentgateway.dev/docs/standalone/latest/documentation/about/introduction/
- Forbes《Agent2Agent Joins The Agentic AI Foundation Alongside MCP》(2026-08)：https://www.forbes.com/sites/janakirammsv/2026/08/19/agent2agent-joins-the-agentic-ai-foundation-alongside-mcp
- O-mega《MCP vs A2A in 2026》（协议全景、ACP 合并、AGNTCY/NANDA、AP2/x402）：https://o-mega.ai/articles/mcp-vs-a2a-in-2026-which-agent-protocol-to-use
- Dreaming Press《A2A vs ACP vs AGNTCY》（三层栈、ACP 归档、SLIM）：https://dreaming.press/posts/a2a-vs-acp-vs-agntcy-agent-interop-protocols.html
- David Prat《How enterprises are wiring AI in 2026》（LangGraph Agent Server `/a2a/{assistant_id}`、kagent、Agent Stack 双控制面）：https://www.davidprat.com/posts/how-enterprises-are-wiring-ai-2026
- Alice Labs《A2A Protocol Guide 2026》（各云 GA 状态、MAF A2A 包、跨云网络实践）：https://alicelabs.ai/en/insights/a2a-protocol-guide-2026
- Nagent AI《AI Agent Marketplace for Enterprise (2026)》（各厂商市场与治理面）：https://nagent.ai/resources/blog/enterprise-ai-agent-marketplace-beyond-the-shelf
- Tray.ai《Best AI agent builders 2026》（Agentforce / Gemini Enterprise / ServiceNow / AgentCore 定价与取舍）：https://tray.ai/blog/best-ai-agent-builders
