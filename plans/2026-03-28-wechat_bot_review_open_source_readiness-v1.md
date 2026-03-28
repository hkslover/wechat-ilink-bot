# WeChat Bot SDK 代码 Review 与开源发布改进计划

## Objective

为当前 `wechat-ilink-bot` 项目制定一份可直接交给后续 AI 执行的审查与改进计划，目标是：

- 系统性 review 现有实现，优先修复影响稳定性、易用性、可维护性与开源发布质量的问题。
- 在不偏离参考实现的前提下，提升 Python SDK 的 API 体验、运行时行为、错误处理、测试覆盖与代码风格。
- 重写 `examples/` 与 `README.md`，让首次接入、日常使用、故障排查、GitHub 开源展示与 PyPI 发布都更顺畅。
- 当协议或行为存在疑问时，以参考仓库 `tencent-weixin:openclaw-weixin/` 为第一对照源，尤其关注 API 行为、账号状态、配置缓存、文档结构与发布质量。参考来源：`tencent-weixin:openclaw-weixin/README.md:17-57`、`tencent-weixin:openclaw-weixin/README.md:90-98`、`tencent-weixin:openclaw-weixin/src/api/api.ts:33-74`、`tencent-weixin:openclaw-weixin/src/api/config-cache.ts:8-78`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:293-319`

## Initial Assessment

### Project Structure Summary

- 当前项目采用清晰的分层结构：高层用户接口集中在 `Bot`，底层 HTTP 封装在 `WeChatClient`，收消息轮询在 `Poller`，消息上下文封装在 `MessageContext`，状态持久化由 `Storage` 管理。这说明项目具备继续演进为稳定 SDK 的基础，但也意味着 review 时必须分别覆盖 API 设计、运行时控制、状态管理与文档层。来源：`src/wechat_bot/bot.py:47-389`、`src/wechat_bot/client.py:59-264`、`src/wechat_bot/polling.py:29-177`、`src/wechat_bot/context.py:49-169`、`src/wechat_bot/storage.py:17-202`
- 包导出面较为友好，`__init__.py` 已整理对外 API，但版本信息存在重复定义，后续发布时容易漂移。来源：`src/wechat_bot/__init__.py:36-77`、`src/wechat_bot/client.py:28-41`、`pyproject.toml:5-47`
- 项目已具备基础测试、示例与打包配置，适合做“开源前整备”。但 README、examples 与真实能力之间仍存在差距。来源：`tests/test_bot.py:1-71`、`tests/test_client.py:1-125`、`README.md:1-97`、`examples/echo_bot.py:1-19`、`examples/proactive_send.py:1-34`

### Relevant Files Examination

- `src/wechat_bot/bot.py`：决定用户如何初始化、登录、注册 handler、发送消息与启动运行，是可用性与 API 风格的核心。若这里不够一致，整个库都会显得难用。来源：`src/wechat_bot/bot.py:69-188`、`src/wechat_bot/bot.py:194-389`
- `src/wechat_bot/client.py`：封装 getUpdates / sendMessage / getUploadUrl / getConfig / sendTyping 五个核心接口，是协议一致性与错误处理的关键。来源：`src/wechat_bot/client.py:173-264`
- `src/wechat_bot/polling.py`：决定长轮询的重试、退避与 session 失效恢复；这里的策略会直接影响 bot 在生产中的可恢复性。来源：`src/wechat_bot/polling.py:83-177`
- `src/wechat_bot/storage.py`：负责 token、当前账号、sync 游标、context token 的持久化；这里既影响安全性，也影响多账号体验。来源：`src/wechat_bot/storage.py:86-202`
- `src/wechat_bot/context.py`：决定 handler 中的回复体验、媒体下载体验与 typing 行为，是“好不好用”的关键触点。来源：`src/wechat_bot/context.py:79-169`
- `examples/*.py` 与 `README.md`：直接决定新用户首次接入成功率，也是后续 GitHub 展示与 PyPI 页面转化率的核心。来源：`README.md:14-89`、`examples/login_bot.py:12-26`、`examples/media_bot.py:16-50`
- 参考实现 `tencent-weixin:openclaw-weixin/`：适合用于协议行为核对、配置缓存策略、账号管理、发布元数据与文档结构借鉴。来源：`tencent-weixin:openclaw-weixin/src/api/api.ts:33-121`、`tencent-weixin:openclaw-weixin/src/api/config-cache.ts:8-78`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:48-107`、`tencent-weixin:openclaw-weixin/package.json:1-24`

### Ranked Challenges and Risks

1. **凭证与状态持久化的安全性/多账号可预期性不足**  
   原因：当前会把 token 明文写入本地，并自动读取“最近账号”，虽然对 demo 友好，但对真实使用与开源发布都存在风险。来源：`src/wechat_bot/storage.py:77-80`、`src/wechat_bot/storage.py:86-127`、`src/wechat_bot/bot.py:88-102`  
   优先级理由：这类问题同时影响安全、稳定性与用户信任，应优先于样式优化。

2. **运行时异常与 session 失效恢复策略不够友好**  
   原因：session 过期后当前策略是长时间暂停，而不是向上层暴露清晰恢复路径；这对实际 bot 运行非常不利。来源：`src/wechat_bot/polling.py:105-119`、`README.md:77-83`  
   优先级理由：这是“机器人失联但不明显”的高风险问题，应该在开源前明确处理。

3. **版本、元数据与发布信息存在漂移风险**  
   原因：版本号在多个位置重复出现，项目 URL 还是占位值，不利于后续发版与维护。来源：`src/wechat_bot/__init__.py:77`、`src/wechat_bot/client.py:28-41`、`pyproject.toml:6-7`、`pyproject.toml:44-47`  
   优先级理由：PyPI/GitHub 开源后，元数据错误会直接损害专业度。

4. **README / examples 未充分覆盖现有能力与关键使用场景**  
   原因：代码已经支持主动发视频、typing、voice 相关处理，但文档与示例没有系统呈现。来源：`src/wechat_bot/bot.py:213-219`、`src/wechat_bot/context.py:144-148`、`src/wechat_bot/handlers.py:78-81`、`README.md:53-89`、`examples/proactive_send.py:13-30`  
   优先级理由：这会明显增加用户误解与使用成本，尤其是在 GitHub 首次浏览场景下。

5. **内部实现存在可维护性重复点，测试覆盖对运行时路径不够强**  
   原因：媒体发送逻辑在多个模块重复，polling/auth/context 等高风险路径测试信号较弱。来源：`src/wechat_bot/bot.py:221-290`、`src/wechat_bot/context.py:117-142`、`src/wechat_bot/context.py:177-215`、`tests/test_bot.py:1-71`、`tests/test_client.py:1-125`  
   优先级理由：这类问题不会立刻爆炸，但会提高后续迭代成本。

## Assumptions and Clarity Assessment

- 假设该库的首要定位是“开发者可直接使用的 Python WeChat bot SDK”，而不是仅供内部脚本调用，因此 API 命名、一致性、错误提示、文档结构、示例质量都需要按公开库标准提升。依据：`README.md:3-18`、`pyproject.toml:6-13`
- 假设后续发布到 PyPI 与 GitHub 时，希望尽量减少“用户必须阅读源码才能用起来”的情况，因此 README 与 examples 不只是附属品，而是产品的一部分。依据：`README.md:26-89`、`examples/echo_bot.py:1-19`
- 假设协议与行为判断存在不确定性时，优先遵循参考仓库已有的成熟做法，而不是随意重新发明一套机制。依据：`tencent-weixin:openclaw-weixin/src/api/api.ts:205-312`、`tencent-weixin:openclaw-weixin/src/api/config-cache.ts:8-78`
- 假设本轮任务允许对 README 与 examples 做较大幅度重写，并允许对对外 API 做“小而稳”的体验优化，但不建议做破坏性重构。依据：`README.md:1-97`、`examples/login_bot.py:1-26`

## Implementation Plan

- [x] **Task 1. 建立 AI review 执行基线（Status: Completed）**：先按“用户体验、运行稳定性、安全性、可维护性、开源发布质量”五个维度扫描全项目，输出问题清单并按严重级排序。重点检查 `Bot`、`WeChatClient`、`Poller`、`Storage`、`MessageContext` 与 examples/README 之间是否存在行为不一致、隐式假设或 API 断层。这样做可以确保后续修改不是零散 patch，而是围绕一个统一的质量目标推进。来源：`src/wechat_bot/bot.py:47-389`、`src/wechat_bot/client.py:59-264`、`src/wechat_bot/polling.py:29-177`、`src/wechat_bot/context.py:49-169`、`README.md:1-97`
- [x] **Task 2. 先处理高风险状态管理与凭证持久化问题（Status: Completed）**：review 并改进 token 与 current user 的本地存储策略，至少补足文件权限、读写原子性、异常时的容错策略，以及多账号场景下“自动选中最近账号”的可解释性。必要时增加更明确的账号选择入口或行为说明。这样做可以优先降低安全风险与误用概率。来源：`src/wechat_bot/storage.py:67-127`、`src/wechat_bot/storage.py:157-202`、`src/wechat_bot/bot.py:88-102`、`tencent-weixin:openclaw-weixin/src/auth/accounts.ts:183-211`
- [x] **Task 3. 重构 session 失效、网络异常与轮询恢复策略（Status: Completed）**：审查 `Poller` 的错误分层，对 session 过期、短期网络失败、服务端异常、长轮询 timeout 分别给出更清晰的处理路径，避免“静默长时间休眠”。目标是让使用者能够更容易知道 bot 是否离线、是否需要重新登录、是否可以自动恢复。来源：`src/wechat_bot/polling.py:91-177`、`src/wechat_bot/client.py:173-202`、`README.md:71-83`
- [x] **Task 4. 统一版本与发布元数据来源（Status: Completed）**：review 项目版本号、包名、App 标识、项目 URL、作者信息等元数据，消除重复定义与占位内容，建立单一可信来源，避免 SDK header、PyPI 元数据与代码内版本出现漂移。这样做可以显著提升发版稳定性和专业度。来源：`pyproject.toml:5-47`、`src/wechat_bot/__init__.py:77`、`src/wechat_bot/client.py:28-41`、`tencent-weixin:openclaw-weixin/src/api/api.ts:33-74`
- [x] **Task 5. 统一并精简消息发送/媒体发送的内部实现（Status: Completed）**：审查 `Bot` 与 `MessageContext` 中重复的媒体发送、caption 组装、CDNMedia 构造、消息分发逻辑，抽象成更稳定的一套内部流程，减少未来协议变化时的多处同步修改成本。这样做的重点是“统一行为与降低维护成本”，不是追求过度抽象。来源：`src/wechat_bot/bot.py:221-290`、`src/wechat_bot/context.py:117-142`、`src/wechat_bot/context.py:177-215`
- [x] **Task 6. 打磨对外 API 的一致性与可理解性（Status: Completed）**：review `Bot`、`MessageContext`、`Filter` 的命名、参数、错误提示、默认行为与 docstring，补齐对开发者真正重要的语义，例如：handler 是否只执行第一个匹配项、typing 在什么条件下有效、Bot 在什么情况下会自动加载状态等。这样可以把“读源码才能知道”的规则变成可预期行为。来源：`src/wechat_bot/bot.py:133-157`、`src/wechat_bot/bot.py:296-322`、`src/wechat_bot/context.py:79-148`、`src/wechat_bot/handlers.py:25-184`
- [x] **Task 7. 参考源库补强配置/会话相关韧性（Status: Completed）**：针对 `get_config`、typing ticket 获取、多次重复请求等行为，评估是否需要引入轻量缓存、退避策略或更明确的失败降级。此项应优先参考源库的成熟模式，而不是自行猜测协议。来源：`src/wechat_bot/context.py:144-148`、`src/wechat_bot/client.py:220-264`、`tencent-weixin:openclaw-weixin/src/api/config-cache.ts:8-78`
- [x] **Task 8. 补齐运行时关键路径测试（Status: Completed）**：在现有单元测试基础上，优先增加对 polling 重试、session 过期、登录边界、context 回复/下载、metadata 同步、examples 可运行性的验证，确保本轮 review 不是只“看起来更漂亮”，而是真正可回归。来源：`tests/test_bot.py:1-71`、`tests/test_client.py:1-125`、`src/wechat_bot/auth.py:89-182`、`src/wechat_bot/polling.py:83-177`、`src/wechat_bot/context.py:88-169`
- [x] **Task 9. 重新设计 examples，使其覆盖真实使用旅程（Status: Completed）**：重写 `examples/`，至少覆盖“首次登录”“最小 echo”“命令式 handler”“媒体下载”“主动发送文本/图片/视频/文件”“多账号/状态目录说明”这些用户真正会遇到的路径。每个示例都应单一职责、可直接运行、命名清晰，并和 README 中的教程顺序保持一致。来源：`examples/echo_bot.py:1-19`、`examples/login_bot.py:1-26`、`examples/media_bot.py:1-50`、`examples/proactive_send.py:1-34`、`src/wechat_bot/bot.py:194-219`
- [x] **Task 10. 重新撰写 README，按开源项目标准组织内容（Status: Completed）**：重构 README 结构，建议覆盖：项目定位、特性、安装、快速开始、登录流程、最小 bot、媒体能力、状态目录、多账号说明、常见错误、测试方式、发布信息、参考实现说明。文档要突出“上手快”和“遇到问题能定位”，并删除机器本地路径等不可移植内容。来源：`README.md:1-97`、`pyproject.toml:44-47`、`tencent-weixin:openclaw-weixin/README.md:17-57`、`tencent-weixin:openclaw-weixin/README.md:90-98`、`tencent-weixin:openclaw-weixin/README.md:236-283`
- [x] **Task 11. 对照 PyPI/GitHub 发布标准做最终收尾（Status: Completed）**：在代码与文档 review 完成后，检查包元数据、license、分类器、可选依赖说明、仓库地址、发版前验证命令、版本策略与对外 API 稳定性，确保项目在开源主页与包索引页上都显得完整可信。来源：`pyproject.toml:1-67`、`LICENSE:1-21`、`src/wechat_bot/__init__.py:36-77`
- [x] **Task 12. 输出一轮 review 结果与后续维护约束（Status: Completed）**：在本轮改进完成后，总结哪些行为被明确、哪些兼容性被保留、哪些风险仍需后续关注，并将“遇到协议问题先对照参考仓库”的规则写入后续 review 约束中，避免未来贡献者偏离基线。来源：`tencent-weixin:openclaw-weixin/README.md:90-98`、`tencent-weixin:openclaw-weixin/src/api/api.ts:205-312`

## Progress Update (2026-03-28)

- 已完成：12 / 12（Task 1-12）
- 部分完成：0 / 12
- 当前阻塞：无代码阻塞
- 后续维护约束：
  - 协议行为疑问优先对照 `tencent-weixin:openclaw-weixin/`，避免凭经验改协议。
  - 所有行为变更必须同步更新 README/examples/tests（至少两者以上）。
  - 发布前固定执行：`ruff`、`pytest`、`build`、`twine check`。
  - 对外 API 变更默认走非破坏式演进；若有破坏性变化必须在 `CHANGELOG.md` 标注。

## Verification Criteria

- [x] 凭证存储、多账号选择、session 过期恢复等高风险路径均有明确行为定义，且行为能从代码与文档中同时看出来。依据关注点：`src/wechat_bot/storage.py:86-202`、`src/wechat_bot/polling.py:91-177`、`README.md:71-83`
- [x] 对外 API 行为保持一致：发送消息、回复消息、媒体发送、handler 匹配、typing 等场景的命名、默认值与错误提示更清晰，避免隐藏规则。依据关注点：`src/wechat_bot/bot.py:133-157`、`src/wechat_bot/bot.py:194-389`、`src/wechat_bot/context.py:79-169`
- [x] examples 能覆盖主要使用路径，且 README 中每个关键步骤都能对应到一个可运行的示例。依据关注点：`examples/echo_bot.py:1-19`、`examples/login_bot.py:1-26`、`examples/media_bot.py:1-50`、`examples/proactive_send.py:1-34`
- [x] README 适合公开仓库展示与 PyPI 页面阅读，不再包含占位仓库地址、机器本地路径或只能靠源码理解的关键规则。依据关注点：`README.md:85-89`、`pyproject.toml:44-47`
- [x] 版本、项目元数据与 SDK 请求头相关信息具备单一来源，减少发版时的人为失误。依据关注点：`src/wechat_bot/__init__.py:77`、`src/wechat_bot/client.py:28-41`、`pyproject.toml:6-7`
- [x] 针对 polling、auth、context、storage 等关键路径新增或完善测试，保证改动后可回归验证。依据关注点：`tests/test_bot.py:1-71`、`tests/test_client.py:1-125`

## Potential Risks and Mitigations

1. **参考源库与当前 Python SDK 的产品边界并不完全一致，盲目照搬会造成过度设计。**  
   Mitigation: 只借鉴协议核对、缓存/恢复思路、账号状态管理与文档结构，不机械复制全部实现；优先保持 Python SDK 的轻量与直观。

2. **为了提升易用性而调整 API，可能引入兼容性变化。**  
   Mitigation: 优先采取非破坏式改进；若必须调整默认行为，应保留兼容路径并在 README/examples 中同步解释。

3. **文档与示例重写后，如果没有同步测试，会出现“文档可读但实际跑不通”的情况。**  
   Mitigation: 将 examples 可运行性纳入验证清单，并补充对应测试或最少 smoke-check。

4. **多账号与自动加载逻辑修改不当，可能影响现有用户的便捷体验。**  
   Mitigation: 保留快捷路径，同时增加显式账号选择能力与更清晰的状态说明，让“简单场景仍简单，复杂场景不混乱”。

5. **过度追求代码风格统一，可能把本来简单的模块抽象得太复杂。**  
   Mitigation: 只消除明确重复、模糊边界和高风险逻辑，不做为了“看起来高级”而产生的抽象。

## Alternative Approaches

1. **渐进式整备方案**：先做高风险修复（storage、polling、metadata、tests），再重写 examples/README。  
   Trade-off: 风险更低、适合稳步推进，但文档与体验改善会稍晚体现。

2. **开源发布优先方案**：先重做 README、examples、metadata 与 API 易用性，再逐步补 runtime 深层修复。  
   Trade-off: 更快改善外部观感，但若底层稳定性问题未先解决，容易出现“宣传很好、运行体验一般”的反差。

3. **参考实现对齐优先方案**：以 `openclaw-weixin` 的行为与结构为基准，优先补齐缓存、账号管理、文档深度。  
   Trade-off: 协议一致性更强，但可能让 Python SDK 失去当前简洁优势，需要谨慎控制复杂度。

4. **Python SDK 产品化优先方案（推荐）**：参考源库的成熟思路，但围绕 Python 开发者体验重新组织 API、错误处理、示例与文档。  
   Trade-off: 需要更多判断与取舍，但最符合“更容易使用、更方便调用、风格更好、便于维护、适合开源与 PyPI”的目标。
