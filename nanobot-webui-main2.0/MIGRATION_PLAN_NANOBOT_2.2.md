# nanobot-main2.2 迁移计划

更新时间：2026-06-25（已补充定制功能迁移分析、WebUI 联调与危险命令防御落地结论）

## 2026-06-25 升级落地记录

本节专门记录今天这一轮把 `nanobot-main2.2` 真正跑到 WebUI 上时，暴露出来的实际问题、根因和修复结论。

这部分内容的目标不是重复“计划”，而是为将来升级 `nanobot-main3.0` 提供可直接复用的经验，减少重新阅读和重新分析的成本。

### 一、今天确认过的核心结论

1. `nanobot-main2.2` 本体已经补齐：
   - `--tool-policy`
   - `--oracle-config`
   - `--oracle-audit`
   - `--oracle-memory`
   - `DangerousToolPolicy`
   - Oracle audit / memory 主链
   - `subagent -> audit_sink`

2. WebUI 启动脚本已经切到 `nanobot-main2.2` 的运行环境：
   - `nanobot-webui-main2.0\start_webui_dba1.bat`
   - Python 已改为 `nanobot-main2.2\.venv\Scripts\python.exe`

3. 仅仅修改启动脚本还不够，WebUI 进程内部还必须把这些参数继续透传给 `AgentLoop.from_config(...)`。

4. 危险命令防御是否生效，不能只看“参数有没有传”，还要同时检查：
   - WebUI 是否把参数透传进 `AgentLoop`
   - 规则是否真的写入 `runtime\tool_policy.json`
   - SQL / Shell 文本是否真的命中规则
   - `mode` 是 `block` 还是 `warn`

5. `warn` 的当前产品语义已经明确：
   - 命中后立即暂停执行
   - 聊天内提示用户审批
   - 用户回复 `approve` / `同意执行` 才继续
   - 用户回复 `cancel` / `拒绝` 则取消
   - 当前不是按钮弹窗式审批，而是“文本审批”

### 二、今天遇到的实际问题与根因

#### 1. WebUI Oracle 页面报 `python-oracledb is not installed`

现象：

- WebUI 的 Oracle 配置 / 知识库相关页面报缺少 `python-oracledb`

定位：

- `nanobot-webui-main2.0\webui\oracle_config.py`
- `nanobot-webui-main2.0\webui\api\routes\knowledge_base.py`

根因：

- WebUI 运行环境已经切到 `nanobot-main2.2\.venv`
- 但该虚拟环境中最开始没有安装 `oracledb`

处理结论：

- 在 `nanobot-main2.2\.venv` 中安装 `oracledb`
- 后续如果升级 `3.0`，必须第一时间检查：
  - WebUI 实际使用的是哪个 Python
  - 该 Python 中是否已安装 `oracledb`

经验：

- 这类问题优先怀疑“运行环境”和“解释器”是否切换成功，而不是先怀疑业务代码。

#### 2. 危险命令防御参数在 WebUI 中未真正生效

现象：

- `start_webui_dba1.bat` 明明已经带了：
  - `--tool-policy`
  - `--oracle-config`
  - `--oracle-audit`
  - `--oracle-memory`
- 但 WebUI 聊天里的危险命令防御和 Oracle 链路并没有按预期工作

根因：

- `nanobot-webui-main2.0\webui\__main__.py` 中，WebUI 创建 `AgentLoop.from_config(...)` 时，最开始没有继续透传：
  - `tool_policy_path`
  - `oracle_config_path`
  - `oracle_audit_enabled`
  - `oracle_memory_enabled`

修复：

- 在 `webui\__main__.py` 中补上：
  - `tool_policy_path=tool_policy_file`
  - `oracle_config_path=oracle_config_file`
  - `oracle_audit_enabled=oracle_audit`
  - `oracle_memory_enabled=oracle_memory`

关键结论：

- 以后升级 `3.0` 时，不能只检查启动脚本。
- 必须同时检查 WebUI 内部创建 `AgentLoop` 的位置是否继续把所有定制参数传入。

#### 3. `block` 能拦，`warn` 没触发，不一定是审批流坏了

现象：

- `truncate table TEST1` 这类 `block` 场景能通过策略判定验证出来
- 但 `ALTER SYSTEM FLUSH SHARED_POOL` 仍然直接执行

根因：

- 不是 `warn` 审批流坏了
- 而是当前 `runtime\tool_policy.json` 里最开始根本没有 `flush shared_pool` 的规则
- 没命中规则，自然不会停下来等待审批

修复：

- 在 `nanobot-webui-main2.0\runtime\tool_policy.json` 中新增：
  - `\balter\s+system\s+flush\s+shared_pool\b`
  - `mode = warn`

验证结果：

- 用实际 MCP 调用参数做预检：
  - 工具名：`mcp_oracle-sqlcl_run-sql`
  - 参数：`{"sql": "ALTER SYSTEM FLUSH SHARED_POOL;", ...}`
- 当前结果已经变成：
  - `ToolApprovalRequiredError`
  - `waiting for user approval`

关键结论：

- 以后升级 `3.0` 时，凡是“看起来应该被拦截但没拦”的问题，先分两层排查：
  1. 参数透传和执行链是否接通
  2. 规则文件是否真的存在对应规则

#### 4. Defense 页面新增规则后刷新消失

现象：

- 在 WebUI 的 Defense 页面添加规则后，页面内看得到
- 一刷新页面规则就消失

根因：

- 前端页面 `web\src\pages\Defense.tsx` 原本的“保存规则”只修改了前端内存状态
- 真正写回 `runtime\tool_policy.json` 只有点“保存策略”才会调用 `/api/tool-policy`

修复：

- 将 Defense 页面改成：
  - 新增规则时立即调用 `/api/tool-policy`
  - 编辑规则时立即调用 `/api/tool-policy`
  - 删除规则时立即调用 `/api/tool-policy`
- 刷新页面后规则不再丢失

关键结论：

- 以后升级 `3.0` 时，所有“策略页 / 配置页 / 管理页”都要检查：
  - 页面内保存是“只改 state”
  - 还是“已经真实落盘”

### 三、今天验证过的真实 MCP 参数样例

为了后续升级时快速复现危险命令防御问题，这里记录今天抓到的真实 MCP 调用形式：

1. `truncate table` 场景：

```json
{
  "tool_name": "mcp_oracle-sqlcl_run-sql",
  "arguments": {
    "sql": "TRUNCATE TABLE TEST1;",
    "model": "GPT-4o"
  }
}
```

2. `flush shared_pool` 场景：

```json
{
  "tool_name": "mcp_oracle-sqlcl_run-sql",
  "arguments": {
    "sql": "ALTER SYSTEM FLUSH SHARED_POOL;",
    "model": "UNKNOWN-LLM"
  }
}
```

关键结论：

- `DangerousToolPolicy` 当前确实能命中 `mcp_oracle-sqlcl_run-sql`
- 真实命中字段是 `arguments.sql`
- 后续升级时，验证 SQL 风险规则不必猜工具结构，优先按这个真实参数格式做回归验证

### 四、今天补回的 2.0 自定义工具

今天已经把 `2.0` 里这 3 个工具迁回 `nanobot-main2.2`，并确认它们现在位于 `nanobot-main2.2\nanobot\agent\tools\` 下，会被 `ToolLoader` 自动扫描和注册，不需要额外手工注册。

#### 1. `win_ssh_linux`

用途：

- 通过 Windows OpenSSH 从当前机器连接 Linux 主机
- 支持：
  - `ssh_exec`
  - `scp_upload`
  - `scp_download`

实现要点：

- 工具名：`win_ssh_linux`
- 依赖环境变量：`OPENSSH_HOME`
- 若未配置 `OPENSSH_HOME`，会尝试默认路径：`E:\OpenSSH-Win64`
- 关键参数包括：
  - `mode`
  - `host`
  - `username`
  - `keyName`
  - `command`
  - `localPath`
  - `remotePath`
  - `port`
  - `strictHostKeyChecking`

使用引导：

- 描述里已经明确要求：
  - 当从 Windows 侧通过 ssh 执行多个 Linux 命令时，优先使用 `bash -lc`
  - 示例：`bash -lc "hostname; date; uptime"`

后续升级 `3.0` 时的复查点：

- 新版本工具加载器是否仍自动扫描 `nanobot\agent\tools`
- `OPENSSH_HOME` 解析逻辑是否还兼容 Windows 部署方式
- 参数别名 `keyName/localPath/remotePath` 是否仍被保留

#### 2. `just_print_file`

用途：

- 直接读取目标文件内容，并把文件内容原样作为最终回复返回用户
- 适合：
  - 用户显式说要“直接显示文件内容”
  - 用户使用 `/print_file`

实现要点：

- 工具名：`just_print_file`
- 和普通 `read_file` 的区别：
  - `read_file` 主要是给模型继续分析
  - `just_print_file` 是直接把文件内容输出给用户
- `just_print_file` 不是普通字符串工具返回值，而是返回：
  - `DirectToolResponse`
- 因此迁移时不能只迁工具文件，还必须同步迁移 `AgentRunner` 中的直出处理分支

本次已经补齐的链路：

- 工具实现：`nanobot-main2.2\nanobot\agent\tools\just_print_file.py`
- Runner 直出分支：`nanobot-main2.2\nanobot\agent\runner.py`
- `/print_file` 提示增强链：`nanobot-main2.2\nanobot\agent\loop.py`

`/print_file` 提示链说明：

- 当用户消息中显式包含 `/print_file` 时，会自动在当前轮消息后追加一段 system note
- 该提示会明确告诉模型：
  - 用户要的是 direct file output
  - 如果已经找到或生成目标文件，优先使用 `just_print_file`
  - 不要总结文件内容

后续升级 `3.0` 时的复查点：

- `AgentRunner` 是否仍支持 `DirectToolResponse`
- `/print_file` 的意图增强函数是否仍挂在消息构建入口
- `just_print_file` 是否仍要求“单独调用”，不能和其它工具同一轮一起执行

#### 3. `open_html`

用途：

- 用系统默认浏览器打开：
  - 本地 HTML 文件
  - `file://` URI
  - `http/https` URL

实现要点：

- 工具名：`open_html`
- 设计目标是：
  - 优先用这个工具预览 HTML
  - 不要再用 `exec` 去执行 `cmd /c start`、PowerShell `Start-Process` 或 Linux `xdg-open`

使用引导：

- 工具描述里已经明确要求：
  - 当要预览生成的 HTML 时，优先使用 `open_html`
- 对 Linux 环境还额外检查：
  - `DISPLAY`
  - `WAYLAND_DISPLAY`

后续升级 `3.0` 时的复查点：

- 新版本文件路径解析是否仍兼容 `file://`
- 默认浏览器调用是否仍然允许
- 如果新版本引入更严格沙箱，需要确认 `open_html` 没有被默认禁用

#### 4. 这三个工具在 `2.0` 中如何更容易被模型选中

今天专门回看后确认：

- `2.0` 并没有为 `win_ssh_linux`、`open_html`、`just_print_file` 单独做一套 onboarding 向导提示
- `2.0` 的 `ContextBuilder` / `build_system_prompt()` 中，也没有为这三个工具写专门的固定 system prompt 段落
- 这三个工具在 `2.0` 中更容易被模型选中的主要原因，其实是：
  - 工具自身 `description` 写得比较具体
  - `just_print_file` 有一条额外的 `/print_file` 局部消息增强链

结论：

- `onboarding` 不适合承载这三个工具的提示，因为它只负责配置向导，不参与每轮工具选择
- 真正适合补的位置是通用 system prompt，即 `nanobot-main2.2\nanobot\templates\agent\tool_contract.md`

本次已做的补充：

- 在 `tool_contract.md` 中新增 `Tool Selection Hints`，明确告诉模型：
  - `/print_file` 或“直接显示文件内容”时优先用 `just_print_file`
  - 预览 HTML 时优先用 `open_html`
  - Windows 到 Linux 的 OpenSSH / SCP 操作时优先用 `win_ssh_linux`

关键结论：

- `2.2` 现在这三层已经都有了：
  - 工具描述
  - `just_print_file` 的 `/print_file` 局部增强
  - `tool_contract.md` 中的通用工具选择提示
- 因此当前判断是：
  - 不需要再把这三个工具塞进 onboarding
  - 但把它们补进 system prompt 是值得的，而且已经完成

#### 5. 本次对 `nanobot` 文件修改低效循环的优化

背景：

- 在真实 Web 测试中，`nanobot` 遇到“把一段 SQL 插入已有脚本”这类简单单文件任务时，曾出现明显低效行为：
  - 同一文件被反复 `read_file`
  - 多次 `edit_file` / `apply_patch`
  - 中途就频繁跑运行验证
  - 典型现象是：本来只需 `读一次关键上下文 -> 改一次 -> 验一次` 的任务，被做成多轮试错编辑

第一版优化目标：

- 先解决最明显的低效循环
- 让模型更接近“先定位、再一次性修改、最后最小验证”的工作流

第一版实现方式：

- 在 `nanobot-main2.2\nanobot\templates\agent\tool_contract.md` 中增加文件修改约束：
  - 单文件简单修改优先走 `read_file -> patch -> verify`
  - 不要在同一片段上来回 `read_file / apply_patch`
  - 不要用运行命令替代文本确认
- 在 `apply_patch.py` / `filesystem.py` 的工具描述里，补充“少做 trial patch、少反复读取同一范围”的提示
- 在 `nanobot-main2.2\nanobot\utils\runtime.py` 中加入第一版运行时限流：
  - 对重复读取同一文件同一范围做拦截
  - 也尝试对同一文件的重复读写/重复编辑进行总次数限流
- 在 `nanobot-main2.2\nanobot\agent\runner.py` 中为每个 turn 增加这些计数器，并在工具执行前调用限流函数

第一版暴露出来的问题：

- 在后续真实测试中，虽然低效行为明显减少，但又出现了另一个问题：
  - 当文件里存在多个相似 SQL 块时，模型会先遇到 `old_text appears 2 times`
  - 随后它可能已经成功写入了一部分核心改动
  - 但因为“同一文件总触碰次数太多”，收尾修正阶段也会被提前拦住
- 这说明“按同一文件总次数限流”太粗了，会把“有效推进后的收尾”误判成低效试错

第二版优化目标：

- 不是简单放宽阈值
- 而是专门解决：
  - 多命中
  - 部分成功
  - 收尾被拦

第二版实现方式：

- 保留“重复读同一未变化范围”的预拦截，因为这类行为基本确定是低效
- 取消“同一文件总触碰次数”这种粗颗粒写入限流
- 改成“结果驱动限流”：
  - 只对连续无进展的编辑失败进行计数
  - 成功写入后立即重置该文件的失败预算
- 在 `runtime.py` 中新增：
  - `_is_file_edit_success()`
    - 识别 `Successfully edited` / `Successfully wrote` / `Patch applied` 这类成功写入结果
  - `_file_edit_failure_kind()`
    - 把失败分成：
      - `ambiguous`：`old_text appears ...`
      - `not_found`：`old_text not found ...`
      - `tool_error`：普通编辑工具错误
  - `repeated_failed_file_edit_error()`
    - 只有当同一文件连续出现多次“无进展失败”时，才升级成 stop-trying 提示
    - 并且根据失败类型给出不同纠偏建议
- 在 `runner.py` 中改成：
  - 保留 `identical_file_read_counts`
  - 移除第一版粗颗粒的 `file_edit_counts` / `file_touch_counts`
  - 改用 `failed_file_edit_counts`
  - 在工具返回结果后再调用 `repeated_failed_file_edit_error()` 做判断
- 也就是说：
  - `read_file` 的无效重复仍然在工具执行前拦
  - 文件编辑是否要限流，改为看“这次执行结果有没有推进”

当前效果：

- 现在 `nanobot` 会更倾向：
  - 先定位稳定锚点
  - 先用较小但足够的上下文做一次修改
  - 改完先回读确认，不急着跑运行验证
- 如果只是“同一文件里有两个相似块，需要二次修正”，不会因为前面已经有过几次尝试就直接被拦住
- 只有在同一文件上连续多次出现：
  - `old_text appears ...`
  - `old_text not found ...`
  - 或连续工具级编辑错误
  这类“无进展失败”时，才会触发升级提示

这次改动涉及的主要文件：

- `nanobot-main2.2\nanobot\templates\agent\tool_contract.md`
  - 增加文件修改工作流约束
  - 增加 `Single-File Edit Playbook`
  - 增加 `Edit Anti-Patterns`

- `nanobot-main2.2\nanobot\agent\tools\apply_patch.py`
  - 在工具描述中强调：简单已知单文件修改，优先一次有计划的 patch，而不是多次 trial patch

- `nanobot-main2.2\nanobot\agent\tools\filesystem.py`
  - 在 `read_file` / `edit_file` 描述中补充：
    - 不要反复读同一未变化范围
    - 不要用 repeated tiny replacements 试探锚点

- `nanobot-main2.2\nanobot\utils\runtime.py`
  - 第一版加入：
    - 重复同一读范围的识别与拦截
  - 第二版改成：
    - 成功写入识别
    - 失败类型分类
    - 连续无进展失败限流

- `nanobot-main2.2\nanobot\agent\runner.py`
  - 为每个 turn 增加文件修改限流相关状态
  - 在文件工具返回结果后，根据“本次是否成功推进”决定是否升级限流

- `nanobot-main2.2\tests\utils\test_workspace_violation_throttle.py`
  - 新增文件读取/文件编辑限流的单元测试
  - 覆盖：
    - 重复读同一范围
    - 连续 ambiguous 失败
    - 连续 not_found 失败
    - 成功写入后预算重置

- `nanobot-main2.2\tests\agent\test_runner_safety.py`
  - 新增 runner 级集成测试
  - 覆盖：
    - 连续失败时会升级
    - 中途成功写入后，后续收尾不会再被误拦

- `nanobot-main2.2\tests\agent\test_runner_tool_execution.py`
  - 跟随 `runner._execute_tools()` 参数调整，更新测试调用

后续升级 `3.0` 时的复查点：

- `tool_contract.md` 中这套文件修改工作流是否仍保留
- `runtime.py` 中是否仍保留：
  - 重复读同一范围的预拦截
  - 文件编辑成功识别
  - 文件编辑失败分类
  - 连续无进展失败限流
- `runner.py` 中是否仍然是“结果驱动限流”，而不是退回到“同一文件总次数限流”
- 新版本文件工具返回文案是否有变化：
  - 如果 `Successfully edited` / `Patch applied` / `old_text appears` / `old_text not found` 这些关键文本变了，需要同步更新识别逻辑
- 如果后续真实测试再出现“多命中 SQL 块”场景，优先检查是否需要进一步增强：
  - `occurrence`
  - `line_hint`
  - `expected_replacements`
  - 或更大上下文锚点 patch 的引导

### 五、今天修改过、后续升级要优先复查的文件

#### 1. `nanobot-webui-main2.0`

- `start_webui_dba1.bat`
  - WebUI 启动入口
  - 已切到 `nanobot-main2.2\.venv`
  - 已透传 `--tool-policy` / `--oracle-config` / `--oracle-audit` / `--oracle-memory`

- `webui\__main__.py`
  - WebUI 内部创建 `AgentLoop` 的关键接线点
  - 后续升级 `3.0` 时必须先看这里有没有丢定制参数透传

- `runtime\tool_policy.json`
  - 危险命令防御的真实运行配置
  - 规则是否生效，最终以这里为准

- `web\src\pages\Defense.tsx`
  - Defense 页面规则编辑与持久化逻辑
  - 已修成增删改立即落盘

- `webui\tool_policy.py`
  - Defense 页面后端保存服务

- `webui\oracle_config.py`
  - Oracle 配置页面逻辑
  - 直接依赖 `oracledb`

- `webui\api\routes\knowledge_base.py`
  - 知识库页面 Oracle 入口
  - 直接依赖 `oracledb`

#### 2. `nanobot-main2.2`

- `nanobot\agent\tool_policy.py`
  - 危险命令规则加载和匹配主模块

- `nanobot\agent\runner.py`
  - `_preflight_tool_policy()`
  - `_check_tool_policy()`
  - `_publish_audit()`
  - `DirectToolResponse` 直出分支

- `nanobot\agent\loop.py`
  - 审批状态机
  - `pending_tool_approval`
  - `approved_tool_call`
  - `approve / 同意执行 / cancel / 拒绝`
  - `/print_file -> just_print_file` 提示增强链

- `nanobot\agent\tools\win_ssh_linux.py`
  - Windows OpenSSH 到 Linux 的 ssh/scp 工具
  - 依赖 `OPENSSH_HOME`

- `nanobot\agent\tools\just_print_file.py`
  - 文件内容直出工具
  - 依赖 `runner.py` 的 `DirectToolResponse` 分支

- `nanobot\agent\tools\open_html.py`
  - HTML/URL 打开工具
  - 用于替代 `exec + start/xdg-open`

- `nanobot\templates\agent\tool_contract.md`
  - 通用 system prompt 中的工具使用约定
  - 已新增这三个工具的选择提示
  - 已新增文件修改工作流、`Single-File Edit Playbook`、`Edit Anti-Patterns`

- `nanobot\oracle_memory.py`
  - Oracle audit / memory 写入服务

- `nanobot\utils\runtime.py`
  - 文件修改低效循环识别与结果驱动限流
  - 重复读同一范围预拦截
  - 连续无进展编辑失败升级

- `nanobot\session\manager.py`
  - `message_id`
  - `message_seq`
  - message observer

- `nanobot\agent\subagent.py`
  - `subagent -> audit_sink`

### 六、如果以后升级 nanobot-main3.0，建议先读本文件后按这个顺序做

1. 先确认新版本 CLI 是否仍保留：
   - `AgentLoop`
   - `AgentRunner`
   - `SessionManager`
   - `SubagentManager`
   - WebUI 创建 `AgentLoop` 的入口

2. 先检查启动脚本切到哪个 Python，再检查该 Python 是否安装：
   - `oracledb`
   - 其它定制链路依赖

3. 先检查 WebUI 创建 `AgentLoop` 时，是否还在透传：
   - `tool_policy_path`
   - `oracle_config_path`
   - `oracle_audit_enabled`
   - `oracle_memory_enabled`

4. 再检查 `runtime\tool_policy.json` 是否被真正加载、真正持久化

5. 最后用真实 MCP 参数做定点验证，不要只看页面现象：
   - `mcp_oracle-sqlcl_run-sql`
   - `arguments.sql`

### 七、给未来升级的简化检查清单

以后如果升级 `3.0`，建议先按下面清单快速过一遍：

- 启动脚本是否已经切到新版本 Python
- 新版本 Python 是否已经安装 `oracledb`
- WebUI 内部是否把 Oracle / Tool Policy 参数继续传给 `AgentLoop`
- Danger Policy 规则是否真的落在 `runtime\tool_policy.json`
- Defense 页面新增规则后刷新是否仍存在
- `block` 场景是否能直接阻断
- `warn` 场景是否会停下来要求回复 `approve` / `同意执行`
- `/print_file` 是否仍能引导模型优先使用 `just_print_file`
- `just_print_file` 是否仍会直接输出文件内容，而不是再总结一轮
- `open_html` / `win_ssh_linux` 是否仍能被工具加载器自动发现
- `tool_contract.md` 中这三个工具的选择提示是否仍保留
- 文件修改限流是否仍然保持“重复读预拦截 + 编辑结果驱动限流”
- 成功写入后是否仍会重置失败预算，避免收尾阶段被误拦
- `subagent` 是否仍继续进入 audit / memory 链

如果上面这些点先确认，再开始读代码，后续分析量会明显下降。

## 目标

本次迁移的总体目标分三阶段推进：

1. 先不处理 `nanobot-main2.0` 上的本地定制功能。
2. 先保证 `nanobot-main2.2` 与 `nanobot-webui-main2.0` 最终可以兼容。
3. 在官方 `2.2` 基线跑通后，再回补 `2.0` 时代额外加上的定制能力。

本轮迁移遵循“先跑通 CLI，再切 WebUI，再补定制”的顺序，避免一开始就把问题混在一起。

## 阶段划分

### 第一阶段：先让 nanobot-main2.2 的 CLI 模式可启动、可测试

目标：

- 先让 `nanobot-main2.2` 自身在 CLI 模式下 build / 启动可用。
- 修改根目录的 `start_cli_dba1.bat`，使其启动链路切换到 `nanobot-main2.2`。
- 启动后由人工进行第一轮验证，确认 CLI 基础能力正常。

当前已知情况：

- 现有 `start_cli_dba1.bat` 仍然使用 `nanobot-webui-main2.0` 自己目录下 `.venv\Scripts\nanobot.exe`。
- 现有脚本使用：
  - `runtime\config.webui.json`
  - 工作目录 `E:\nanobot-main\dba1`
- 这意味着第一步不是改 WebUI，而是先把 CLI 启动链切到 `nanobot-main2.2` 并跑通。

本阶段任务：

1. 梳理 `nanobot-main2.2` 的安装/运行方式
2. 准备 `nanobot-main2.2` 所需环境
3. 修改 `start_cli_dba1.bat`
4. 让脚本优先启动 `nanobot-main2.2`
5. 输出启动说明，交由人工测试
6. 根据测试结果修正 CLI 启动参数或环境

本阶段完成标志：

- 双击或命令行执行 `start_cli_dba1.bat` 后，能够启动到 `nanobot-main2.2` 的 CLI
- 你可以手工完成一轮基础测试
- CLI 不再依赖旧的 `nanobot-main2.0` 启动链

### 第二阶段：调整 nanobot-webui-main2.0，使其切换到 nanobot-main2.2

目标：

- 保留当前 `nanobot-webui-main2.0` 作为前端/管理端基础。
- 将其后端调用、接口适配和运行时兼容层切换到 `nanobot-main2.2`。
- 完成最小可用兼容改造，让 WebUI 能连上 `2.2` 并正常工作。

改造原则：

- 优先兼容官方 `2.2`，不在这一阶段引入 `2.0` 定制功能。
- 先保证主流程可用：
  - 登录/鉴权
  - 会话列表
  - 聊天收发
  - WebSocket
  - 基础配置读取
  - 常用页面不报错

本阶段主要工作：

1. 对照 `nanobot-main2.2` 的接口和目录结构
2. 审查 `nanobot-webui-main2.0` 当前依赖的接口入口
3. 找出不兼容点并建立兼容清单
4. 调整 WebUI 后端转发层、补丁层、适配层
5. 调整前端字段映射与页面兼容逻辑
6. 联调 chat / session / ws / config 等核心路径
7. 修复因 `2.2` 新结构引起的运行错误

优先兼容模块：

- `webui/api/gateway.py`
- `webui/api/server.py`
- `webui/api/routes/`
- `webui/patches/`
- `web/src/lib/api.ts`
- `web/src/lib/ws.ts`
- `web/src/hooks/`
- `web/src/pages/Chat.tsx`

本阶段完成标志：

- `nanobot-webui-main2.0` 能连接 `nanobot-main2.2`
- WebUI 主界面可以正常使用
- 核心聊天链路可用
- 主要页面不因接口不兼容而崩溃

### 第三阶段：补做 nanobot-main2.0 定制功能在 nanobot-main2.2 上的实现

目标：

- 在官方 `2.2` 基线和 WebUI 兼容完成后，再回补 `2.0` 的本地增强功能。

本阶段明确延后处理的内容：

- Oracle audit 存储
- Oracle memory 存储
- `tool_call` 阶段危险命令防御增强
- `open_html`
- `win_ssh_linux`
- 其它只存在于 `2.0` 本地分支的增强逻辑

原因：

- 这些功能不是官方 `2.2` 原生功能。
- 如果一开始就一起迁移，会把“官方升级问题”和“本地定制迁移问题”混在一起，定位成本太高。
- 先让 `2.2 + webui-main2.0` 跑通，后面再逐项移植更稳。

本阶段工作方式：

1. 基于已经跑通的 `2.2` 主链路
2. 逐项比较 `2.0` 的定制实现
3. 按优先级回补到 `2.2`
4. 每补一项就做单项验证

优先回补顺序建议：

1. Oracle audit
2. 危险命令防御审批链
3. Oracle memory
4. 自定义工具
5. 其它定制项

## 第三阶段分析

本节专门记录当前准备迁回 `nanobot-main2.2` 的两类定制能力：

1. `--tool-policy`
2. `--oracle-config` + `--oracle-audit` + `--oracle-memory`

这部分本次先做分析和计划，不直接在本文件里记录实施结果。

### 一、`nanobot-main2.0` 的危险命令防御实现情况

#### 1. 启动参数与配置文件

- 启动开关依赖 `--tool-policy "%TOOL_POLICY%"`。
- 当前配置文件位置：`nanobot-webui-main2.0\runtime\tool_policy.json`。
- 规则文件结构已经固定，包含：
  - `command`
  - `matchType`
  - `regexFlags`
  - `category`
  - `severity`
  - `mode`
  - `scope`
  - `note`

#### 2. 规则加载与匹配模块

- 核心模块是 `nanobot-main2.0\nanobot\agent\tool_policy.py`。
- 该模块负责：
  - 加载 JSON 规则文件
  - 支持 `literal` / `regex` 两种匹配方式
  - 递归扫描 tool call 参数中的字符串字段
  - 产出 `block` 或 `warn` 决策
  - 判断“这次执行是否已经被用户明确批准过”

#### 3. Runner 阶段接入方式

- 核心接入点是 `nanobot-main2.0\nanobot\agent\runner.py`。
- `AgentRunner.__init__()` 在 `2.0` 中新增了：
  - `audit_sink`
  - `tool_policy`
- `runner.py` 有两层防护：
  - `_preflight_tool_policy()`：在一批 tool call 执行前先扫一次
  - `_check_tool_policy()`：在单个工具真正执行前再检查一次
- 行为分支：
  - `block`：直接阻断，不执行工具
  - `warn`：暂停执行，要求用户明确回复 `approve` / `同意执行`

#### 4. Loop 阶段审批状态机

- 核心接入点是 `nanobot-main2.0\nanobot\agent\loop.py`。
- `AgentLoop.__init__()` 在 `2.0` 中新增了：
  - `tool_policy_path`
- `AgentLoop` 会创建：
  - `self.tool_policy = DangerousToolPolicy(tool_policy_path)`
  - `self.runner = AgentRunner(provider, audit_sink=self.oracle_memory, tool_policy=self.tool_policy)`
- `loop.py` 还维护了会话级审批状态：
  - `pending_tool_approval`
  - `approved_tool_call`
- 用户回复以下内容会被解释为批准：
  - `同意`
  - `同意执行`
  - `approve`
  - `yes`
  - `continue`
- 用户回复以下内容会被解释为拒绝：
  - `拒绝`
  - `取消`
  - `deny`
  - `cancel`
  - `stop`

#### 5. 当前能力边界

- `exec` 工具自身还有一层命令黑名单，这是工具级兜底。
- `DangerousToolPolicy` 是更通用的“tool_call 参数级”防御，可覆盖：
  - Shell 命令
  - SQL
  - 其它文本型危险参数
- 真正需要迁回 `2.2` 的是：
  - 规则加载器
  - Runner 双层检查
  - Loop 审批状态机
  - CLI 参数透传

### 二、`nanobot-main2.0` 的 Oracle audit / memory 实现情况

#### 1. 启动参数与配置文件

- 启动参数包括：
  - `--oracle-config "%ORACLE_CONFIG%"`
  - `--oracle-audit`
  - `--oracle-memory`
- 当前配置文件位置：`nanobot-webui-main2.0\runtime\oracle_config.json`
- 当前配置内容支持：
  - `user`
  - `password`
  - `dsn`
  - 也兼容 `host + port + service_name` 组合

#### 2. Oracle 写入服务

- 核心模块是 `nanobot-main2.0\nanobot\oracle_memory.py`。
- 模块核心类：`OracleMemoryService`
- 该服务负责：
  - `publish_audit()`
  - `publish_memory()`
  - `publish_session_message()`
  - 异步队列批量写入 Oracle
  - 写入失败只记日志，不阻塞主链路
- 当前写入两张表：
  - `NB_AGENT_AUDIT`
  - `NB_AGENT_MEMORY`

#### 3. Audit 接入方式

- 核心接入点是 `nanobot-main2.0\nanobot\agent\runner.py`。
- `runner.py` 中新增 `_publish_audit()`。
- 每次 LLM 请求结束后会采集：
  - `request_messages_json`
  - `request_tools_json`
  - `request_options_json`
  - `response_json`
  - `usage`
  - `finish_reason`
  - `error_kind / error_type / error_code`
- 然后通过 `audit_sink.publish_audit(payload)` 入队。

#### 4. Memory 接入方式

- 核心接入点在两处：
  - `nanobot-main2.0\nanobot\session\manager.py`
  - `nanobot-main2.0\nanobot\agent\loop.py`
- `session\manager.py` 在 `2.0` 中新增：
  - `message_id`
  - `message_seq`
  - message observer
- `loop.py` 中：
  - `self.sessions.set_message_observer(self._on_session_message_persisted)`
  - observer 内部调用 `self.oracle_memory.publish_session_message(...)`
- 这表示 `memory` 入库依赖 `session` 层补齐“稳定消息标识”和“消息持久化观察者”。

### 三、`nanobot-main2.2` 当前与 `2.0` 的差异

#### 1. CLI 还没有这些参数

- `nanobot-main2.2\nanobot\cli\commands.py` 的 `agent` 命令当前只有：
  - `--message`
  - `--session`
  - `--workspace`
  - `--config`
  - `--markdown`
  - `--logs`
- 还没有：
  - `--tool-policy`
  - `--oracle-config`
  - `--oracle-audit`
  - `--oracle-memory`

#### 2. `AgentLoop` 还没有定制功能接入点

- `nanobot-main2.2\nanobot\agent\loop.py` 当前构造函数里没有：
  - `tool_policy_path`
  - `oracle_memory_enabled`
  - `oracle_audit_enabled`
  - `oracle_config_path`
  - `oracle_memory`
- `self.runner = AgentRunner(provider)` 仍是官方原版形态。

#### 3. `AgentRunner` 还是官方无产品逻辑版本

- `nanobot-main2.2\nanobot\agent\runner.py` 当前：
  - 没有 `audit_sink`
  - 没有 `tool_policy`
  - 没有 `_publish_audit()`
  - 没有 `_preflight_tool_policy()`
  - 没有 `_check_tool_policy()`
- `AgentRunSpec` 里也没有：
  - `turn_id`
  - `channel`
  - `chat_id`
  - `tool_approval_callback`
  - `approved_tool_call`
  - `model_preset`

#### 4. `Session` 基础能力在 `2.2` 中也缺失一部分

- `nanobot-main2.2\nanobot\session\manager.py` 当前没有：
  - `message_id`
  - `message_seq`
  - message observer
- 这意味着 Oracle memory 不能只迁 `oracle_memory.py`，还必须补 `session` 层。

#### 5. `SubagentManager` 也回到了官方简化版

- `nanobot-main2.2\nanobot\agent\subagent.py` 当前内部也是 `AgentRunner(provider)`。
- 如果后续要求 subagent 的模型请求也进入 Oracle audit，`subagent.py` 也要一起补。

### 四、迁移实施计划

#### 任务 A：先在 `nanobot-main2.2` 恢复 CLI 参数

目标：

- 让 `nanobot-main2.2` 的 CLI 启动时可接受：
  - `--tool-policy`
  - `--oracle-config`
  - `--oracle-audit`
  - `--oracle-memory`

计划改动文件：

- `nanobot-main2.2\nanobot\cli\commands.py`

实施说明：

- 先只给 `agent` 命令加参数。
- 后续如 WebUI 或 gateway 也要直接透传，再补对应命令。

#### 任务 B：把 `DangerousToolPolicy` 迁入 `nanobot-main2.2`

目标：

- 让 `2.2` 恢复基于 `tool_policy.json` 的危险命令判定。

计划改动文件：

- 新增或恢复 `nanobot-main2.2\nanobot\agent\tool_policy.py`
- 修改 `nanobot-main2.2\nanobot\agent\runner.py`
- 修改 `nanobot-main2.2\nanobot\agent\loop.py`

实施顺序：

1. 迁入 `DangerousToolPolicy`、`ToolPolicyRule`、`ToolPolicyDecision`
2. 扩展 `AgentRunSpec`
3. 扩展 `AgentRunner.__init__()`
4. 恢复 `_preflight_tool_policy()`
5. 恢复 `_check_tool_policy()`
6. 在 `AgentLoop` 中补会话级审批状态机

验证点：

- `mode = block` 的规则会直接阻断工具执行
- `mode = warn` 的规则会暂停并提示用户审批
- 用户回复 `approve` / `同意执行` 后，下一轮允许同一 tool call 执行

#### 任务 C：把 `OracleMemoryService` 迁入 `nanobot-main2.2`

目标：

- 让 `2.2` 恢复：
  - `--oracle-audit`
  - `--oracle-memory`
  - `--oracle-config`

计划改动文件：

- 新增或恢复 `nanobot-main2.2\nanobot\oracle_memory.py`
- 修改 `nanobot-main2.2\nanobot\agent\loop.py`
- 修改 `nanobot-main2.2\nanobot\agent\runner.py`
- 修改 `nanobot-main2.2\nanobot\session\manager.py`

实施顺序：

1. 迁入 `OracleMemoryService`
2. 给 `AgentLoop.__init__()` / `from_config()` 增加 Oracle 相关参数
3. 在 `AgentRunner` 恢复 `_publish_audit()`
4. 在 `Session` / `SessionManager` 恢复 `message_id`、`message_seq`、observer
5. 在 `AgentLoop` 中把 observer 绑定到 `publish_session_message()`
6. 在关闭链路中确保 `await self.oracle_memory.close()`

验证点：

- 打开 `--oracle-audit` 后，LLM 调用会写入 `NB_AGENT_AUDIT`
- 打开 `--oracle-memory` 后，session 消息会写入 `NB_AGENT_MEMORY`
- 不安装 `python-oracledb` 或数据库不可达时，只记日志，不阻塞 CLI

#### 任务 D：处理 `2.2` 独有结构带来的迁移差异

重点说明：

- `2.2` 的 `AgentRunSpec` 与 `2.0` 不同，迁移时不能直接覆盖整个文件。
- `2.2` 的 `Session.get_history()` 已新增 `extend_to_user`，迁移 `session` 时必须保留这个能力。
- `2.2` 有 `runtime_events`、`workspace scope`、新的 WebUI 配套模块，迁移时要尽量局部补丁，不要回滚官方结构。

建议策略：

- 只补“缺失字段”和“缺失调用点”
- 不回退 `2.2` 已有的官方行为
- 每个任务单独做验证，避免一次性大改

### 五、建议实施顺序

当前建议的编码顺序如下：

1. 先补 `tool_policy.py`
2. 再补 `AgentRunSpec` 和 `AgentRunner` 的危险命令防御链
3. 再补 `AgentLoop` 的审批状态机
4. 完成 `--tool-policy` CLI 参数接入并测试
5. 再迁 `oracle_memory.py`
6. 再补 `runner.py` 的 audit
7. 再补 `session\manager.py` 的 memory 基础能力
8. 最后接入 CLI 的 `--oracle-config` / `--oracle-audit` / `--oracle-memory`

### 六、当前结论

- 这两类功能在 `2.0` 中都不是简单脚本功能，而是已经接进主执行链。
- 危险命令防御的最小闭环是：
  - CLI 参数
  - policy loader
  - runner 双层检查
  - loop 审批状态机
- Oracle audit / memory 的最小闭环是：
  - CLI 参数
  - OracleMemoryService
  - runner audit 上报
  - session observer + message identity
- 迁移时要以 `2.2` 为底座做“局部回补”，不能简单拿 `2.0` 文件整块覆盖。

## 当前执行顺序

本周期开工顺序固定如下：

1. 先改 `start_cli_dba1.bat`
2. 先把 `nanobot-main2.2` CLI 跑起来
3. 由人工先测 CLI
4. 再开始改 `nanobot-webui-main2.0`
5. 再做 `2.0` 定制功能迁移

## 当前决策

当前已经明确以下策略：

- 不以 `nanobot-main2.0` 定制功能作为第一阶段阻塞项
- 第一优先级是 `nanobot-main2.2` CLI 可启动
- 第二优先级是 `nanobot-webui-main2.0` 对接 `nanobot-main2.2`
- 第三优先级才是补齐 `2.0` 定制增强

## 下一步

下一步直接进入第一阶段实施：

1. 检查 `nanobot-main2.2` 的 CLI 运行环境
2. 修改 `start_cli_dba1.bat`
3. 让你手工启动并验证
