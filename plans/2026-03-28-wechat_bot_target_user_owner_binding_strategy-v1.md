# WeChat Bot 单用户绑定与目标用户参数优化计划

## Objective

为当前 `wechat-ilink-bot` 制定一份关于“目标用户（to / target_user）是否还需要显式传入”的专项 review 与改进计划，目标是：

- 基于当前项目实现与参考仓库 `tencent-weixin:openclaw-weixin/`，重新梳理这个库的“收发消息目标用户模型”。
- 判断在腾讯当前 bot 机制下，`to_user_id` 在协议层、SDK 层、Webhook 层、Examples/README 层分别应当如何保留、隐藏或弱化。
- 给后续 AI 一个清晰的改造方向：既能兼容“当前大概率只有 bot 创建者本人可对话”的现实约束，又不把 SDK 设计死，保留未来腾讯开放“一 bot 对多个用户”时的扩展空间。
- 优先提升易用性与默认行为，同时避免因为过度简化而破坏协议兼容性或未来能力扩展。

## Initial Assessment

### Project Structure Summary

- 当前 Python SDK 在主动发送路径上，统一要求调用者显式提供目标用户 `to`。无论是 `send_text()`、`send_image()`、`send_video()` 还是 `send_file()`，都需要外部传入目标用户 ID。来源：`src/wechat_bot/bot.py:236-299`
- 当前回复路径并不需要额外传目标用户，因为它直接从入站消息 `from_user_id` 构造出站消息目标，这本质上说明“对话上下文内”已经可以自动推导收件人。来源：`src/wechat_bot/context.py:88-103`、`src/wechat_bot/context.py:117-142`
- 当前项目已经在登录结果与本地存储中持久化了 `user_id`，这意味着“机器人创建者/扫码者”这一身份信息其实已经存在，只是还没有在主动发送 API 中被真正利用。来源：`src/wechat_bot/bot.py:205-230`、`src/wechat_bot/storage.py:126-165`
- README、examples、webhook 目前都把 `to` 视为必填输入，因此现有用户心智仍然是“主动发送必须指定目标用户”。来源：`README.md:73-121`、`examples/proactive_send.py:13-35`、`src/wechat_bot/webhook.py:15-21`、`src/wechat_bot/webhook.py:72-137`

### Relevant Files Examination

- `src/wechat_bot/bot.py`：决定主动发送 API 是否必须要求 `to`，也是未来引入默认 owner 用户、自动推导 recipient、兼容模式开关的核心文件。来源：`src/wechat_bot/bot.py:236-299`
- `src/wechat_bot/context.py`：说明“回复消息”本来就不需要外部显式传目标用户，因此它可以作为“自动目标推导”的现有设计参考。来源：`src/wechat_bot/context.py:88-103`
- `src/wechat_bot/storage.py`：已经保存 `user_id`，适合扩展为 owner/默认接收者判断依据。来源：`src/wechat_bot/storage.py:126-165`
- `src/wechat_bot/webhook.py`：当前 GET/POST `/send` 都要求 `to`，如果要优化这个参数体验，这里是必须同步评估的入口。来源：`src/wechat_bot/webhook.py:15-21`、`src/wechat_bot/webhook.py:72-137`
- `README.md` 与 `examples/proactive_send.py`：目前都把 `WECHAT_TARGET_USER` 当作必要配置，这决定了用户当前的接入方式。来源：`README.md:73-121`、`examples/proactive_send.py:13-35`

### Reference Source Findings

- 参考实现的协议发送层仍然明确使用 `to_user_id`，也就是从底层协议看，发送消息给谁仍是一个显式字段，而不是可省略字段。来源：`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`、`tencent-weixin:openclaw-weixin/README.md:136-155`
- 参考实现的媒体上传请求 `GetUploadUrlReq` 也包含 `to_user_id`，说明不仅发送消息，连上传媒体准备阶段也依赖目标用户上下文。来源：`tencent-weixin:openclaw-weixin/src/api/types.ts:19-40`
- 参考实现并没有彻底取消 `to`；它只是在“当前会话上下文发送给当前用户”这类上层框架场景中，允许调用方不手填 `to`，因为宿主框架已经知道当前会话对象是谁。来源：`tencent-weixin:openclaw-weixin/src/channel.ts:165-170`
- 对于定时任务/非当前会话发送，参考实现反而特别强调必须显式提供 `to` 和 `accountId`，否则会失败或发错 bot。来源：`tencent-weixin:openclaw-weixin/src/channel.ts:170-172`
- 参考实现会在 QR 登录后保存 `userId`，并清除同一个 `userId` 关联的旧账号，防止多个 accountId 与同一用户产生歧义。这强烈说明“同一微信用户重新创建/绑定新 bot 后，旧 bot/旧账号可能已不再是推荐使用对象”，至少在工程上他们就是按“新覆盖旧”的思路在处理。来源：`tencent-weixin:openclaw-weixin/src/channel.ts:321-339`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`
- 参考实现的命令授权与 pairing 逻辑，也会把登录扫码得到的 `userId` 当作默认允许交互的用户，这与“当前机器人主要面向创建者本人”这一判断是一致的。来源：`tencent-weixin:openclaw-weixin/src/messaging/process-message.ts:179-185`、`tencent-weixin:openclaw-weixin/src/auth/pairing.ts:78-119`

### Ranked Challenges and Risks

1. **如果直接从 SDK 所有发送 API 中删除 `to`，会破坏底层协议显式性，也会降低未来扩展性。**  
   证据：协议请求本身仍要求 `to_user_id`，媒体上传也要求 `to_user_id`。来源：`src/wechat_bot/bot.py:236-299`、`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`、`tencent-weixin:openclaw-weixin/src/api/types.ts:19-40`  
   优先级理由：这是架构层风险，错误决策会影响整个 SDK 长期设计。

2. **如果继续让所有场景都必须手填 `to`，在当前“单用户 bot”现实下会显得啰嗦且不友好。**  
   证据：当前项目已经保存了 `user_id`，但主动发送、webhook、examples 仍要求用户重复提供相同目标。来源：`src/wechat_bot/storage.py:126-165`、`examples/proactive_send.py:13-35`、`src/wechat_bot/webhook.py:72-137`  
   优先级理由：这是当前用户体验最直接的痛点。

3. **如果默认自动把“登录扫码用户”当成唯一目标用户，又不提供显式覆盖能力，会在腾讯后续开放多用户能力时成为技术债。**  
   证据：参考实现对会话场景和非会话场景区分很清楚，说明他们也在避免把“当前单用户限制”写死进底层接口。来源：`tencent-weixin:openclaw-weixin/src/channel.ts:165-172`

4. **同一微信账号重新创建/覆盖 bot 的行为存在不确定性，但参考实现已经按“同 userId 保留新账号、清理旧账号”进行防歧义处理。**  
   证据：他们在登录后清除同 userId 的旧账号数据。来源：`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`、`tencent-weixin:openclaw-weixin/src/channel.ts:321-339`  
   优先级理由：这会影响当前库对 account/user/recipient 的建模方式。

## Assumptions and Clarity Assessment

- 假设腾讯当前开放的 WeChat bot 能力，在绝大多数场景下确实是“一个 bot 主要只服务创建它的那个微信用户”，且主动发送的默认目标通常就是扫码登录返回的 `user_id`。依据：`src/wechat_bot/bot.py:205-230`、`tencent-weixin:openclaw-weixin/src/auth/login-qr.ts:281-305`
- 假设底层协议短期内不会取消 `to_user_id`，因此不能把 `to` 从底层 client / wire model / media upload 请求中完全删除。依据：`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`、`tencent-weixin:openclaw-weixin/src/api/types.ts:19-40`
- 假设真正需要优化的是“高层 SDK 默认行为与用户输入体验”，而不是协议字段本身。依据：`src/wechat_bot/bot.py:236-299`、`src/wechat_bot/context.py:88-103`
- 假设未来腾讯有可能放开“一 bot 对多用户”，因此推荐设计应当是“高层可以省略 `to`，底层仍保留显式 `to`，并允许随时回退到显式模式”。

## Recommended Strategy

推荐采用 **“协议层保留显式 to，SDK 高层引入 owner-aware 默认目标模型”** 的方案：

- **底层协议层 / client 层：继续保留 `to_user_id` 为显式字段**，不改动 wire model 基本语义。依据：`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`
- **高层 Bot API：新增或调整为“可选 to”语义，但只在能安全推导 owner 用户时才省略**。推导来源优先使用登录返回并持久化的 `user_id`。依据：`src/wechat_bot/bot.py:205-230`、`src/wechat_bot/storage.py:126-165`
- **回复路径维持现状**，因为上下文消息已经天然知道目标用户。依据：`src/wechat_bot/context.py:88-103`
- **Webhook/Examples/README：改为 owner-first 体验**，例如允许不传 `to` 时默认发给 owner；同时保留 `to` 参数作为高级/兼容入口。依据：`src/wechat_bot/webhook.py:72-137`、`README.md:73-121`
- **增加显式策略开关或模式说明**，避免未来多用户开放后 API 行为难以解释。可考虑引入类似“strict explicit recipient”与“owner-default recipient”两种模式。

## Implementation Plan

- [x] **Task 1. 先明确 recipient model 的分层边界（Status: Completed）**：已保留协议层显式 `to_user_id`，并在 SDK 高层通过 `resolve_recipient()` 实现 owner-default 推导。
- [x] **Task 2. 审查并定义 owner 用户来源（Status: Completed）**：已实现 owner 来源优先级：`Bot.user_id` -> `credentials.user_id` -> `current_user.user_id(同 account)`。
- [x] **Task 3. 设计高层发送 API 的兼容升级方案（Status: Completed）**：已升级为高层 API 可选 `to`（owner-default），同时保留显式 `to` 路径完全兼容。
- [x] **Task 4. 设计严格的默认推导失败策略（Status: Completed）**：owner 不可用时已明确报错，不进行静默猜测。
- [x] **Task 5. 对 Webhook 层做 owner-first 设计评估（Status: Completed）**：`/send` 的 `to` 已改为可选，并在响应中返回最终目标及来源（`to_source`）。
- [x] **Task 6. 重写 examples 的目标用户叙事（Status: Completed）**：`proactive_send.py`、`account_switch.py`、`webhook_server.py` 已改为 owner-first 示例。
- [x] **Task 7. 重写 README 中的目标用户说明（Status: Completed）**：已新增 owner-default 模型说明，并同步 webhook 示例与参数语义。
- [x] **Task 8. 参考源库补充账号/userId 歧义处理（Status: Completed）**：已新增同 `user_id` 账号聚合能力，并在登录后对同用户多账号给出告警提示，减少覆盖歧义。
- [x] **Task 9. 为 owner-default 行为增加测试矩阵（Status: Completed）**：已补充 `resolve_recipient`、owner-default 发送、webhook 缺省 `to`、owner 缺失报错等测试。
- [x] **Task 10. 最终确定默认策略与兼容策略（Status: Completed）**：默认 owner-first，显式 `to` 优先，owner 不可判定时强制显式 `to`。

## Verification Criteria

- [x] 协议层与 SDK 高层的 recipient 语义被明确区分：底层仍兼容 `to_user_id`，高层在 owner 已知时可降低使用成本。
- [x] 主动发送 API、webhook、examples、README 对“是否必须传 `to`”给出一致规则，不再互相矛盾。
- [x] 当 owner 用户无法确定时，系统不会静默猜测，而是给出清晰可操作的错误提示。
- [x] 对同一 `user_id` 重新登录产生新 account 的情况，已有明确提示策略（登录后告警同 user_id 多账号）。
- [x] tests 能覆盖 owner-default 与 explicit-recipient 两种路径，可支撑后续策略演进。

## Potential Risks and Mitigations

1. **误把当前“owner-only”平台限制当成永久协议事实。**  
   Mitigation: 不删除底层 `to`，只在高层引入 owner-default 体验，并保留显式目标覆盖。

2. **自动推导 owner 目标可能导致误发。**  
   Mitigation: 只有在 owner `user_id` 唯一且可信时才允许省略 `to`；否则强制报错要求显式输入。

3. **Webhook 与脚本示例如果默认省略 `to`，未来多用户开放时行为会突然变得含糊。**  
   Mitigation: 保留 `to` 参数，并在 README 中明确说明“owner-default 是便捷模式，不是协议要求”。

4. **同一用户多次创建 bot 是否会覆盖旧 bot 的事实仍不完全确定。**  
   Mitigation: 参考源库已有做法，把“同 userId 保留最新账号、旧账号做清理或显式标记”纳入 review 范围，而不是假设所有旧账号都仍然可靠。依据：`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`

## Alternative Approaches

1. **彻底删除高层 API 中的 `to` 参数**：所有主动发送默认发给 owner。  
   Trade-off: 当前使用最简单，但未来如果支持多用户会成为明显技术债，不推荐。

2. **完全保留现状，继续要求所有主动发送必须显式传 `to`**：不做语义优化。  
   Trade-off: 兼容最稳，但在当前 owner-only 现实下用户体验不够好，且重复输入无意义。

3. **双轨方案（推荐）**：底层和显式发送接口保留 `to`，同时新增 owner-aware 默认路径，让用户在简单场景可省略目标，在高级场景仍可显式控制。  
   Trade-off: 设计稍复杂，但最符合“当前易用 + 未来可扩展”的平衡。

4. **仅在 Webhook/Examples 层省略 `to`，核心 Bot API 不动**：把便捷性控制在外围入口。  
   Trade-off: 改动最保守，但会造成 README 与 Python API 体验不一致，不够彻底。
