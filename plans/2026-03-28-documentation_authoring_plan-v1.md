# Documentation Authoring Plan

## Objective

基于当前仓库的真实代码能力、测试覆盖与现有文档现状，制定一份可交给 Forge 执行的文档撰写计划，优先重写或补强以下公开文档：`README.md`、`CONTRIBUTING.md`、`SECURITY.md`。目标是让这些文档准确反映 SDK 的安装方式、核心能力、运行约束、贡献流程与安全披露方式，并与当前实现保持一致。

## Initial Assessment

### Project Structure Summary

- 该仓库是一个 Python SDK 项目，采用 `src/` 布局，包名为 `wechat_bot`，并通过 `hatchling` 构建发布；Python 版本基线为 3.10+，运行时依赖主要为 `httpx`、`pydantic`、`cryptography`，并提供 `qrcode`、`socks`、`webhook`、`dev` 等可选依赖。这意味着 README 必须清晰区分基础安装与场景化 extras，贡献文档也应直接复用统一安装入口。来源：`pyproject.toml:1-81`。
- 对外核心接口集中在 `Bot`、`WeChatClient`、`MessageContext`、`Storage`、`Filter`、`MessageHandler` 以及 webhook 工具函数，这表明 README 需要围绕“高层 Bot 用法 + 低层 client 能力 + webhook 扩展”组织信息，而不是只给出单一 quickstart。来源：`src/wechat_bot/__init__.py:1-80`。
- 仓库已包含 `examples/` 与 `tests/`，示例覆盖登录、回声、命令处理、媒体下载、主动发送、账号切换、webhook 启动，测试覆盖 Bot、Webhook、Storage、Polling、Auth 等主要行为。因此文档可以用这些文件作为权威示例来源，并在贡献文档中明确“行为改动必须同步示例与测试”。来源：`README.md:63-71`、`tests/test_examples_smoke.py:25-171`、`tests/test_bot.py:21-242`、`tests/test_webhook.py:37-201`。

### Relevant Files Examination

- `README.md` 已有较完整的中文用户导向内容，覆盖安装、快速开始、示例脚本、owner-default 发送规则、webhook、状态目录、安全策略、FAQ、测试与贡献入口；但其内容较长，适合继续优化结构、补充 API 心智模型与“从安装到生产使用”的路径。来源：`README.md:1-227`。
  - 含义：Forge 在撰写时应以“重构升级”而不是“从零新写”为主，尽量保留已有有效内容并增强信息架构。
- `CONTRIBUTING.md` 当前较短，只包含基础安装、检查命令、代码风格、PR checklist 与 bug 报告要求。它尚未充分解释仓库结构、测试矩阵、示例同步规则、变更分类、可选依赖下的验证范围。来源：`CONTRIBUTING.md:1-46`。
  - 含义：这是最适合显著扩写的文档之一。
- `SECURITY.md` 当前只说明 0.x 支持策略与私下上报渠道，尚未结合本仓库的本地凭证存储、权限控制、token 处理、webhook API key、错误暴露策略等实现细节。来源：`SECURITY.md:1-24`、`src/wechat_bot/storage.py:15-18`、`src/wechat_bot/storage.py:145-175`、`src/wechat_bot/webhook.py:37-47`、`src/wechat_bot/webhook.py:95-103`、`src/wechat_bot/webhook.py:117-141`。
  - 含义：安全文档应从“政策文本”升级为“政策 + 运行安全建议 + 漏洞披露范围”。
- `Bot` 是用户入口，负责自动加载当前账号、账号切换、二维码登录、owner-default 收件人解析、主动发送文本/图片/视频/文件。来源：`src/wechat_bot/bot.py:68-127`、`src/wechat_bot/bot.py:139-207`、`src/wechat_bot/bot.py:249-410`。
  - 含义：README 必须准确解释账号选择、owner-default、重新登录、发送接口的预期行为。
- `Poller` 实现长轮询、失败重试、退避、session 过期恢复与停止信号。这是 README 中“运行时行为”和 CONTRIBUTING 中“测试关注点”的关键内容。来源：`src/wechat_bot/polling.py:21-28`、`src/wechat_bot/polling.py:99-212`。
- `Storage` 实现 `~/.wechat_bot` 状态目录、`current_user.json`、`credentials.json`、`sync.json`、`context_tokens.json`，并使用严格权限与原子替换写入。来源：`src/wechat_bot/storage.py:20-40`、`src/wechat_bot/storage.py:98-120`、`src/wechat_bot/storage.py:145-175`、`src/wechat_bot/storage.py:181-235`。
  - 含义：README 与 SECURITY 都应明确本地状态文件的用途、敏感性与权限假设。
- `webhook.py` 与 `cli.py` 暴露 `wechat-bot webhook` 能力，支持 GET/POST `/send`、API key、禁用 GET、指定 account、统一错误响应。来源：`src/wechat_bot/webhook.py:49-174`、`src/wechat_bot/webhook.py:177-208`、`src/wechat_bot/cli.py:14-71`。
  - 含义：README 需要把 webhook 与 CLI 作为明确的可选功能区块，而 SECURITY 需要解释公网暴露风险与最小化暴露策略。
- `MessageContext`、媒体上传/下载模块体现了“reply / send_typing / download_media / CDN 加解密”的真实能力边界。来源：`src/wechat_bot/context.py:49-173`、`src/wechat_bot/media/upload.py:27-156`、`src/wechat_bot/media/download.py:71-160`。
  - 含义：README 的特性与示例描述应反映这些能力，而不是笼统声称“支持媒体”。

### Prioritized Challenges and Risks

1. **README 需要在“已有内容很多”与“结构更清晰”之间平衡**  
   排名原因：它直接影响首次使用者，且内容最广；若组织不好，会继续出现信息冗长、关键路径不够突出的问题。依据：`README.md:1-227`。
2. **贡献文档与仓库真实流程之间目前存在细节缺口**  
   排名原因：贡献者文档如果不覆盖测试范围、示例同步、changelog 约束、可选依赖验证，后续 PR 质量容易波动。依据：`CONTRIBUTING.md:5-46`、`CHANGELOG.md:8-25`。
3. **安全文档尚未充分承接真实实现中的敏感点**  
   排名原因：仓库确实处理 token、本地凭证、webhook key、错误隐藏，但现有政策文档没有把这些信息转化为安全操作建议。依据：`SECURITY.md:1-24`、`src/wechat_bot/storage.py:126-175`、`src/wechat_bot/webhook.py:117-141`。
4. **示例、测试与文档之间需要建立强一致性**  
   排名原因：该项目已具备良好的示例和测试资产，若文档不以这些资产为事实来源，容易再次出现漂移。依据：`examples/login_bot.py:15-24`、`examples/echo_bot.py:15-28`、`examples/proactive_send.py:13-47`、`tests/test_examples_smoke.py:25-171`。

## Scope and Assumptions

- 本计划默认 Forge 将以“更新现有文档”为主，而不是新增大量新文档；优先处理 `README.md`、`CONTRIBUTING.md`、`SECURITY.md`，必要时仅在这些文档内部增加新章节。依据：`README.md:215-219`。
- 本计划假设当前代码行为优先于旧文案；如旧文案与实现不一致，应以实现与测试为准。依据：`src/wechat_bot/bot.py:189-207`、`tests/test_bot.py:148-242`、`tests/test_webhook.py:103-201`。
- 本计划假设文档受众至少分为三类：初次使用者、功能集成者、仓库贡献者；因此 README、CONTRIBUTING、SECURITY 的职责边界应更明确。

## Implementation Plan

- [x] Task 1. 先建立文档事实基线，整理“项目定位、安装方式、核心公开接口、可选功能、示例入口、测试入口、状态目录与安全行为”这七类事实，并为每一类附上代码依据，避免 Forge 在撰写阶段引用过时描述。理由：当前已有文档内容丰富但分散，先做事实归档可减少后续 README/CONTRIBUTING/SECURITY 相互矛盾的风险。关键依据：`pyproject.toml:5-81`、`src/wechat_bot/__init__.py:1-80`、`src/wechat_bot/bot.py:43-127`、`src/wechat_bot/bot.py:249-410`、`src/wechat_bot/storage.py:20-40`、`src/wechat_bot/webhook.py:49-174`。
- [x] Task 2. 重构 README 的信息架构，建议采用“项目简介 → 适用场景 → 安装与 extras → 5 分钟快速开始 → 示例地图 → 核心行为说明 → webhook/CLI → 状态目录与安全 → FAQ → 开发与测试入口”的顺序，并保留中文主文档定位。理由：现有 README 信息完整，但快速开始、规则说明、webhook、状态目录、FAQ 已经具备较好素材，主要问题是内容层次和首次阅读路径仍可优化。关键依据：`README.md:1-227`。
- [x] Task 3. 在 README 中新增或强化“真实行为说明”章节，至少明确以下规则：`Bot()` 默认自动加载 `current_user.json`、显式 `account_id` 与 `use_current_user=False` 的差异、`send_text/send_image/send_video/send_file` 的 owner-default 规则、owner 无法解析时会报错、handler 首个匹配即停止、polling 的 session 失效后需重新登录。理由：这些是最容易被集成方误解的运行时语义，且已有明确实现与测试支持。关键依据：`src/wechat_bot/bot.py:88-98`、`src/wechat_bot/bot.py:139-207`、`src/wechat_bot/bot.py:293-410`、`src/wechat_bot/handlers.py:159-184`、`src/wechat_bot/polling.py:121-158`、`tests/test_bot.py:148-242`。
- [x] Task 4. 在 README 中把 examples 目录改写为“场景索引”，逐个说明每个脚本解决什么问题、何时使用、依赖哪些环境变量或先置条件，并确保说明与示例源码一致。理由：examples 已是最可靠的上手路径，若 README 只列文件名而不解释适用时机，用户仍需反复读源码。关键依据：`examples/login_bot.py:15-24`、`examples/echo_bot.py:15-28`、`examples/command_bot.py:16-39`、`examples/media_bot.py:16-50`、`examples/proactive_send.py:13-47`、`examples/account_switch.py:15-36`、`examples/webhook_server.py:26-68`。
- [x] Task 5. 扩写 CONTRIBUTING，使其从“检查命令列表”升级为“贡献流程指南”，至少补充：仓库结构概览、开发环境安装、可选依赖验证边界、代码/示例/测试/文档联动要求、PR 范围控制、changelog 更新原则、行为变更应如何补充测试。理由：当前贡献文档过短，无法充分支撑外部贡献者形成一致的提交质量。关键依据：`CONTRIBUTING.md:5-46`、`pyproject.toml:34-50`、`CHANGELOG.md:8-25`、`tests/test_examples_smoke.py:25-171`。
- [x] Task 6. 在 CONTRIBUTING 中明确“验证矩阵”，把至少以下命令和对应目的写清楚：ruff 用于静态检查、pytest 用于行为验证、build/twine check 用于发布前校验，并补充说明当修改 webhook、examples、storage、安全相关行为时，应优先查看哪些测试文件。理由：现有文档只给命令，不给命令与模块之间的关系，新贡献者难以判断自己改动应覆盖哪些区域。关键依据：`CONTRIBUTING.md:14-21`、`tests/test_webhook.py:37-201`、`tests/test_storage.py:14-116`、`tests/test_polling.py:31-82`、`tests/test_auth.py:26-60`。
- [x] Task 7. 重写 SECURITY，使其除了漏洞上报政策外，还包含“本仓库当前安全边界说明”：token 与凭证文件位置、默认不把 token 写入 `current_user.json`、私有权限模式、原子写入、防止 webhook 泄露内部异常、建议使用 API key 并限制监听地址、不要将状态目录提交到版本控制。理由：这些都属于实现层面已经存在的安全设计，文档应显式传达给用户。关键依据：`src/wechat_bot/storage.py:15-18`、`src/wechat_bot/storage.py:98-120`、`src/wechat_bot/storage.py:145-175`、`src/wechat_bot/webhook.py:117-141`、`src/wechat_bot/webhook.py:177-208`、`README.md:171-185`。
- [x] Task 8. 为 SECURITY 增加“supported versions 与披露流程”的可执行措辞，明确 0.x 阶段支持策略、建议提供的最小复现信息、避免公开 issue 披露、修复发布后的协调披露原则，并保持与现有政策兼容。理由：当前政策基础存在，但仍偏简短，可扩展为更适合开源协作的正式安全说明。关键依据：`SECURITY.md:1-24`。
- [x] Task 9. 统一三份文档中的术语与命名，例如 `owner`、`owner-default`、`current_user.json`、`account_id`、`user_id`、`context token`、`webhook key`、`session expired`，避免 README 用业务说法、CONTRIBUTING 用实现说法、SECURITY 用泛化说法。理由：术语漂移会显著增加阅读与维护成本，尤其是在中英混排文档中。关键依据：`README.md:90-96`、`src/wechat_bot/bot.py:134-207`、`src/wechat_bot/storage.py:26-34`、`src/wechat_bot/webhook.py:37-47`。
- [x] Task 10. 撰写完成后做一次“文档-代码一致性回归审查”，逐项核对安装命令、CLI 参数、示例文件名、响应格式、状态目录结构、权限描述、session 处理描述是否仍与当前实现一致。理由：这一步是防止文档更新后再次引入事实错误的最后保险。关键依据：`pyproject.toml:34-53`、`src/wechat_bot/cli.py:18-39`、`src/wechat_bot/webhook.py:105-172`、`src/wechat_bot/storage.py:26-34`、`src/wechat_bot/polling.py:121-158`。

## Verification Criteria

- [ ] `README.md` 中的安装方式、示例入口、webhook/CLI 用法、owner-default 规则、状态目录描述均能在代码中找到对应实现，至少可分别映射到 `pyproject.toml:34-53`、`examples/` 脚本、`src/wechat_bot/cli.py:14-71`、`src/wechat_bot/bot.py:189-207`、`src/wechat_bot/storage.py:26-34`。
- [ ] `CONTRIBUTING.md` 不再只停留在命令清单，而是能指导贡献者完成环境搭建、变更验证、PR 准备与 changelog 更新，并且与现有测试/构建流程一致。依据：`CONTRIBUTING.md:5-46`、`CHANGELOG.md:8-25`、`pyproject.toml:41-50`。
- [ ] `SECURITY.md` 明确说明私下披露方式，并补充与本仓库实际实现一致的安全边界与运行建议。依据：`SECURITY.md:8-24`、`src/wechat_bot/storage.py:145-175`、`src/wechat_bot/webhook.py:117-141`。
- [ ] 三份文档对 `account_id`、`user_id`、`owner-default`、`webhook key` 等关键术语的定义一致，不出现同一概念多种未解释表述。依据：`README.md:82-96`、`src/wechat_bot/bot.py:189-207`、`src/wechat_bot/webhook.py:109-141`。
- [ ] 文档中引用的示例脚本名称、命令参数、默认端口、状态目录路径与当前仓库实际文件一致。依据：`README.md:63-71`、`examples/webhook_server.py:26-68`、`src/wechat_bot/cli.py:18-39`、`src/wechat_bot/storage.py:15-18`。

## Potential Risks and Mitigations

1. **风险：README 继续堆叠内容，导致更完整但更难读。**  
   Mitigation: 采用“快速开始优先、深度说明后置”的结构，并将细节规则收敛到专门章节，避免所有信息都挤在前半部分。依据：`README.md:37-80`、`README.md:150-185`。
2. **风险：文档描述 owner-default、账号切换或 session 过期行为时使用了旧语义。**  
   Mitigation: 所有相关文案以 `Bot` 与 `Poller` 的当前实现和测试断言为准，不以旧 README 文案为准。依据：`src/wechat_bot/bot.py:143-207`、`src/wechat_bot/polling.py:121-158`、`tests/test_bot.py:148-242`。
3. **风险：安全文档写成通用模板，未体现本项目的真实敏感面。**  
   Mitigation: 必须把状态目录、token 存储、权限模式、webhook key、错误隐藏策略写入 SECURITY，而非仅保留“如何报告漏洞”的平台模板。依据：`src/wechat_bot/storage.py:98-120`、`src/wechat_bot/storage.py:145-175`、`src/wechat_bot/webhook.py:95-103`、`src/wechat_bot/webhook.py:117-141`。
4. **风险：贡献文档与测试矩阵脱节，导致外部贡献者只跑最少命令。**  
   Mitigation: 在 CONTRIBUTING 中按改动类型映射测试文件与验证命令，例如 webhook 改动关注 `tests/test_webhook.py:37-201`，账号/发送逻辑关注 `tests/test_bot.py:21-242`，存储与权限关注 `tests/test_storage.py:14-116`。

## Alternative Approaches

1. **方案 A：最小增量更新现有三份文档。**  优点是改动小、合并阻力低；缺点是容易继续受旧结构约束，README 可读性提升有限。适合希望快速完成首轮公开整理的场景。
2. **方案 B：以 README 重构为主、CONTRIBUTING/SECURITY 中度扩写。**  优点是用户侧收益最大，且实施成本仍可控；缺点是贡献流程与安全策略提升幅度可能不如彻底重写。适合优先改善 onboarding 的场景。
3. **方案 C：三份文档统一重写，但严格复用现有章节素材与代码事实。**  优点是整体一致性最好；缺点是 Forge 需要更强的结构控制与更仔细的一致性校对。对于当前仓库已经具备较成熟功能面，这通常是最推荐方案。

## Recommended Execution Order

- [ ] Step 1. 先完成 README 重构，因为它承载项目定位、安装、上手、行为规则与扩展能力，是其余两份文档的入口。依据：`README.md:1-227`。
- [ ] Step 2. 再扩写 CONTRIBUTING，把开发者需要遵守的验证与同步规则固定下来。依据：`CONTRIBUTING.md:5-46`。
- [ ] Step 3. 最后补强 SECURITY，确保其引用 README 中已定稿的状态目录、webhook、安全建议等术语。依据：`SECURITY.md:1-24`、`README.md:171-185`。
