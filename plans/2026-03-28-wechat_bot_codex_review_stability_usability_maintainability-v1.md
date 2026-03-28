# WeChat Bot SDK Codex Review 执行计划（稳定性 / 易用性 / 可维护性）

## Objective

为当前 `wechat-ilink-bot` 项目制定一份可直接交给 Codex 执行的代码 review 与改进计划，目标是：

- 以“提升稳定性、易用性、可维护性”为第一优先级，对现有实现进行系统性审查与改进。
- 围绕当前已经引入的 owner-default / recipient 解析、多账号切换、webhook、轮询恢复、状态持久化等关键能力，继续做一轮面向公开 SDK 的质量 review。
- 让 Codex 在 review 时代码时，不只是修小 bug，而是同时优化 API 语义、错误处理、边界行为、测试信号与维护成本。
- 当协议行为、账号绑定逻辑、recipient 解析策略存在疑问时，优先参考仓库内的 `tencent-weixin:openclaw-weixin/`，尤其关注发送目标语义、账号与 userId 关系、context token、配置缓存、错误恢复策略。参考来源：`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-161`、`tencent-weixin:openclaw-weixin/src/channel.ts:52-102`、`tencent-weixin:openclaw-weixin/src/channel.ts:165-172`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`、`tencent-weixin:openclaw-weixin/src/auth/login-qr.ts:281-305`

## Initial Assessment

### Project Structure Summary

- 当前项目已经形成较清晰的 SDK 分层：`Bot` 负责高层 API 与运行控制，`WeChatClient` 负责协议请求，`Poller` 负责长轮询，`MessageContext` 负责 handler 场景的上下文能力，`Storage` 负责本地状态。这个结构适合继续演进，但也要求 Codex 的 review 不能只盯单点文件，而要覆盖跨层行为一致性。来源：`src/wechat_bot/bot.py:43-260`、`src/wechat_bot/client.py:61-284`、`src/wechat_bot/context.py:49-173`、`src/wechat_bot/polling.py:29-177`、`src/wechat_bot/storage.py:20-260`
- 当前项目已经开始引入 owner-default 目标用户模型：`Bot` 支持通过 `resolve_recipient()` 解析显式 `to` 或 owner `user_id`，Webhook 也允许 `to` 缺失时走 owner 默认值。这说明 API 易用性在提升，但也意味着当前阶段非常需要一轮专门的语义一致性 review。来源：`src/wechat_bot/bot.py:134-207`、`src/wechat_bot/webhook.py:108-170`、`README.md:73-140`
- README、examples、tests 已经初步对齐 owner-default 新行为，但它们是否完全一致、是否存在隐式规则、是否足够稳健，仍值得让 Codex 做二次审查。来源：`README.md:73-140`、`examples/proactive_send.py:13-47`、`tests/test_bot.py:148-198`、`tests/test_webhook.py:49-178`

### Relevant Files Examination

- `src/wechat_bot/bot.py`：这是本轮 review 的中心文件。它同时承载账号选择、owner 推导、主动发送、轮询启动与 session 恢复，是稳定性与易用性的核心交叉点。来源：`src/wechat_bot/bot.py:68-207`、`src/wechat_bot/bot.py:249-260`
- `src/wechat_bot/storage.py`：这是 owner/default recipient、多账号、context token、本地状态恢复的基础数据层。任何 recipient 策略如果没有和 storage 严格对齐，就容易产生行为漂移。来源：`src/wechat_bot/storage.py:126-175`、`src/wechat_bot/storage.py:196-260`
- `src/wechat_bot/webhook.py`：这是最容易暴露给外部用户的 HTTP 入口，错误响应结构、owner-default 行为、认证策略、参数验证都直接影响可用性与运维体验。来源：`src/wechat_bot/webhook.py:15-170`
- `README.md` 与 `examples/proactive_send.py`：当前已经开始把主动发送描述为 owner-default 模式，但仍保留显式 `to`。这套叙事是否足够清晰，是否和真实代码完全一致，适合交给 Codex 继续打磨。来源：`README.md:73-140`、`examples/proactive_send.py:13-47`
- `tests/test_bot.py` 与 `tests/test_webhook.py`：这些测试已经覆盖 owner-default 的主要路径，但仍需要让 Codex 审视是否遗漏关键边界，例如账号切换后的 owner 变化、recipient 歧义、发送失败路径、旧状态兼容。来源：`tests/test_bot.py:81-198`、`tests/test_webhook.py:86-178`
- 参考实现 `tencent-weixin:openclaw-weixin/`：适合帮助判断“高层可以省略 `to`”与“底层协议仍保留 `to_user_id`”之间的边界，同时也能帮助处理同一 `userId` 对应多个本地账号时的歧义问题。来源：`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-161`、`tencent-weixin:openclaw-weixin/src/channel.ts:52-102`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`

### Ranked Challenges and Risks

1. **recipient / owner-default 语义虽然更易用，但跨层一致性风险最高**  
   原因：当前 `Bot`、Webhook、README、examples、tests 都已经开始支持“不传 `to` 默认发给 owner”，但底层协议仍然要求显式 `to_user_id`。如果这层抽象没有彻底统一，后续极易出现某些入口默认发 owner、另一些入口仍强制显式目标的混乱。来源：`src/wechat_bot/bot.py:189-207`、`src/wechat_bot/webhook.py:129-137`、`README.md:90-95`、`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`  
   优先级理由：这会同时影响易用性、行为可预期性和后续维护难度。

2. **owner 推导依赖本地状态，状态不完整时的失败路径必须足够清晰**  
   原因：当前 owner 解析依赖 `_user_id`、credentials、current_user 三层来源；一旦状态缺失、账号切换、旧数据残留或本地多账号冲突，易出现“为什么不能发消息”的用户疑惑。来源：`src/wechat_bot/bot.py:170-207`、`src/wechat_bot/storage.py:141-175`、`tests/test_bot.py:167-170`  
   优先级理由：这类问题经常不是功能错误，而是可解释性不足，公开库中影响很大。

3. **同一个 user_id 绑定多个本地账号时，目前只有 warning，没有完整策略闭环**  
   原因：当前代码已经开始警告“同一 user 绑定多个 account”，但还需要 Codex 判断是否应继续增加清理、标记、显式选择或文档说明策略。来源：`tests/test_bot.py:81-102`、`src/wechat_bot/storage.py:252-260`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`  
   优先级理由：这和你项目的单用户绑定现实强相关，也直接影响维护成本。

4. **Webhook 虽然更简洁，但仍需进一步 review 错误边界、状态码与响应一致性**  
   原因：它已经引入统一响应结构和 owner-default 行为，但还需要确认各种失败场景是否都可预期、可调试、不会泄露不必要内部实现细节。来源：`src/wechat_bot/webhook.py:73-102`、`src/wechat_bot/webhook.py:108-170`、`tests/test_webhook.py:103-178`  
   优先级理由：Webhook 往往最先暴露给使用者，外部体验会直接影响对整个 SDK 的评价。

5. **examples/README 已经更接近产品化，但仍可能存在文档与实际实现的细微偏差**  
   原因：例如 owner-default 与 explicit recipient 的优先级、何时必须显式传 `to`、何时依赖 owner `user_id`、多账号切换如何影响默认目标，都需要文档和示例同步说清楚。来源：`README.md:80-95`、`examples/proactive_send.py:21-45`、`src/wechat_bot/bot.py:189-207`  
   优先级理由：这类偏差不会立即导致崩溃，但会显著增加用户疑惑与维护沟通成本。

## Assumptions and Clarity Assessment

- 假设该库依然以“公开可复用的 Python WeChat bot SDK”为目标，因此本轮交给 Codex 的 review 不应只是修复当前功能，还应同时优化接口直觉性、错误提示可读性与长期维护可持续性。依据：`README.md:3-19`、`README.md:149-167`
- 假设 owner-default 是当前产品体验的重要方向，但不应破坏底层协议层的显式 recipient 语义。依据：`README.md:90-95`、`src/wechat_bot/bot.py:189-207`、`tencent-weixin:openclaw-weixin/src/messaging/send.ts:38-60`
- 假设未来腾讯仍有可能放开多用户或更多账号形态，因此 Codex 在 review 时应优先做“高层默认行为优化”，避免把当前单用户限制写死在所有层。依据：`tencent-weixin:openclaw-weixin/src/channel.ts:165-172`
- 假设同一 `user_id` 出现多个本地账号时，至少需要有一致、明确、面向开发者的说明与行为约束，而不能只靠隐式 warning。依据：`tests/test_bot.py:81-102`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:83-107`

## Implementation Plan

- [x] **Task 1. 让 Codex 先做一次 owner-default 语义一致性审计（Status: Completed）**：已完成跨 `Bot` / Webhook / README / examples / tests 一致性复核，显式 `to` 优先与 owner-default 规则保持一致。
- [x] **Task 2. 审查并强化 owner 解析链路的稳定性（Status: Completed）**：已补齐 owner 回退链路边界测试（credentials、current_user、account mismatch、use_account 后更新）并保留清晰报错。
- [x] **Task 3. 审查主动发送 API 的兼容性与可读性（Status: Completed）**：主动发送 API 保持统一可选 `to` 语义，docstring、README 与示例对齐 owner-default 模式。
- [x] **Task 4. 审查多账号与同 userId 绑定场景（Status: Completed）**：已保留同 userId 多账号 warning，并在文档补充“建议显式设置账号”的操作建议。
- [x] **Task 5. 对 Webhook 做一轮接口稳定性 review（Status: Completed）**：已统一成功/失败响应结构，并覆盖 GET/POST、认证、参数校验、方法禁用、recipient 失败、发送失败路径。
- [x] **Task 6. 让 Codex 对 README/examples 做“用户首次接入”导向的二次 review（Status: Completed）**：已更新文档说明 owner-default、显式 `to` 与多账号建议，示例与行为一致。
- [x] **Task 7. 让 Codex 继续补齐行为测试矩阵（Status: Completed）**：新增 owner 回退边界、explicit 覆盖、account 切换后 owner 更新、webhook 502、examples owner-default 路径测试。
- [x] **Task 8. 审查日志、warning 与错误提示的维护价值（Status: Completed）**：发送失败路径改为服务端记录异常日志并返回通用 502 文案，减少内部异常泄漏。
- [x] **Task 9. 对照参考实现复核 recipient / account 设计边界（Status: Completed）**：保持“协议层显式 recipient + SDK 高层 owner-default”的分层策略，不破坏 account-to-user 语义边界。
- [x] **Task 10. 输出一份可持续维护的 review 结论与约束（Status: Completed）**：已将关键行为收敛为固定基线，并通过 README + tests 固化约束与回归信号。

## Verification Criteria

- [x] owner-default、explicit recipient、Webhook 省略 `to`、多账号切换等关键路径在代码、测试、README、examples 四个层面都保持一致。
- [x] 当 owner 缺失、recipient 无法确定、账号冲突或状态不完整时，系统给出的错误提示清晰、稳定、可操作，不依赖阅读源码才能理解。
- [x] 主动发送 API 的参数设计、默认行为与示例文档相互匹配，不再出现“文档说可省略、代码却不支持”或“测试通过但 README 没讲清”的情况。
- [x] Webhook 在成功、认证失败、参数无效、方法不允许、recipient 无法解析、发送失败等路径上都返回一致且面向外部调用者友好的响应结构。
- [x] 针对同一 `user_id` 的多账号冲突、owner 回退链路、old state 兼容、recipient 解析优先级等路径，具备足够测试覆盖与行为说明。

## Potential Risks and Mitigations

1. **为提升易用性而过度强调 owner-default，导致底层协议语义被模糊。**  
   Mitigation: 继续保留底层显式 `to_user_id`，仅在高层 API 和入口层引入默认推导逻辑。

2. **不同入口对 recipient 的解析逻辑如果稍有偏差，会让维护者很难排查问题。**  
   Mitigation: 让 Codex 优先做跨入口一致性审计，并把 recipient 规则收敛到少数核心方法上。

3. **同一 userId 对应多个本地账号的情况，如果只有 warning 没有清晰文档，后续维护者会反复踩坑。**  
   Mitigation: 要求 Codex 同步补充行为说明、测试覆盖，并评估是否需要更强的约束或显式策略。

4. **Webhook 错误响应过于内部化或过于宽泛，都会影响实际接入体验。**  
   Mitigation: 统一错误响应结构，并逐项审查 400/401/405/422/502/500 的边界与文案。

5. **文档和示例在快速迭代后可能落后于实现。**  
   Mitigation: 将 README/examples/tests 绑定为同一批 review 对象，要求任何行为变更至少同步更新其中两项以上。

## Alternative Approaches

1. **稳定性优先方案**：让 Codex 主要审查 recipient 解析、storage 回退、Webhook 失败路径和多账号边界，暂不进一步扩展 API 表达。  
   Trade-off: 风险最低，但对外体验提升会相对保守。

2. **易用性优先方案**：让 Codex 优先围绕 owner-default、文档与 examples 做体验优化，再逐步补账号冲突与边界行为。  
   Trade-off: 用户第一印象更好，但如果底层边界未收紧，后续维护成本可能上升。

3. **参考实现对齐优先方案**：更严格地参考 `openclaw-weixin` 的 recipient/account 处理方式，对当前 Python SDK 继续收敛策略。  
   Trade-off: 协议层一致性更强，但可能牺牲部分 Python SDK 的简洁直观。

4. **SDK 产品化优先方案（推荐）**：让 Codex 在保持协议兼容的前提下，优先做高层 API、owner-default、Webhook、测试与文档的一致性收敛，使库在公开使用中更稳定、更容易上手、更容易维护。  
   Trade-off: 需要更细致的判断与跨文件 review，但最符合“增加稳定性、易用性，同时有利于其他人维护”的目标。
