---
name: oracle_blog_recent_ai_fetch
description: when user asks to fetch recent AI related news from Oracle blogs, use this skill. Run the local script oracle_blog_recent_ai_fetch.py to collect recent Oracle blog posts, then summarize them in a CSS management and delivery oriented way.
---

# 使用说明

## 作用

这个 skill 用于：

- 抓取 Oracle Blog 最近 30 天内与 AI 相关的文章
- 只关注预设的 Oracle blog 分站
- 根据关键词筛选文章标题
- 抓取文章正文并保存到本地结果文件
- 再对结果做逐篇总结，并给出 CSS 视角建议

## 对应脚本

- 脚本文件：`oracle_blog_recent_ai_fetch.py`
- 逐篇读取工具：`get_blog.py`

## 运行命令

在该 skill 目录下执行：



```bash
python oracle_blog_recent_ai_fetch.py
```
在win平台运行python时，需要先设置
chcp 65001
设置环境变量PYTHONIOENCODING=utf-8

# 用户没有要求取多久的时间范围，默认提取最近 30 天的文章
python oracle_blog_recent_ai_fetch.py

# 提取最近 7 天的文章
python oracle_blog_recent_ai_fetch.py --days 7

# 提取最近 60 天的文章
python oracle_blog_recent_ai_fetch.py --days 60

## 运行前提

当前脚本依赖：

- Python 包：`playwright`
- 浏览器运行时查找顺序：
  1. 环境变量`CHROME_HOME`
     - 也可以指向浏览器所在目录
  2. workspace 根目录
  3. 如果都找不到，则自动回退到 Playwright Chromium

脚本会根据当前操作系统自动尝试常见浏览器可执行文件名：
- Windows: `chrome.exe`, `msedge.exe`, `chromium.exe`
- Linux: `chrome`, `google-chrome`, `chromium`, `chromium-browser`, `msedge`
- macOS: Google Chrome / Chromium / Microsoft Edge 的常见 `.app` 可执行路径

如果回退后浏览器仍无法启动，可执行：

```bash
playwright install chromium
```

## 输出文件

脚本会生成两个文件：

- 文章内容文件：`oracle_ai_blogs_<yyyymmdd>.txt`
- 已读 URL 文件：`has_been_read.txt`

## 去重规则

- 脚本会读取 `has_been_read.txt`
- 已处理过的 URL 会跳过
- 本次新处理的 URL 会追加写入该文件

# 抓取范围与筛选规则

## 博客范围 由代码内部控制
## 文章筛选规则 由代码内部控制
## 当前关键词 由代码内部控制

## 完成blogs抓取后，逐篇读取文章内容的方法

为了确保严格按文章逐篇处理，不要直接一次性读取整份 `oracle_ai_blogs_<yyyymmdd>.txt`。

必须使用 `get_blog.py`：

例如：
1. 先统计文章数：

```bash
python get_blog.py oracle_ai_blogs_20260420.txt
```

输出示例：

```text
article_count=8
```

2. 再按文章号逐篇获取内容：

```bash
python get_blog.py oracle_ai_blogs_20260420.txt 1
python get_blog.py oracle_ai_blogs_20260420.txt 2
python get_blog.py oracle_ai_blogs_20260420.txt 3
```

说明：

- 文章号是从 `1` 开始的
- `python get_blog.py <txt文件>`：只统计文章总数
- `python get_blog.py <txt文件> <文章号>`：输出第 N 篇文章全文
- 如果 txt 中没有获得任何文章，统计结果会是 `article_count=0`


# 分析从 `get_blog.py` 输出的文章内容的后的总结输出
## AI 总结要求

在 `oracle_ai_blogs_<yyyymmdd>.txt` 生成后：

- 绝对不要一次性把所有文章混在一起总结
- 必须先用 `python get_blog.py <txt文件>` 获取文章总数
- 然后用 `python get_blog.py <txt文件> <文章号>` 逐篇处理
- 一次只处理一篇文章,处理的时候如果发现文章主题和AI没有关系，则可以跳过改文章
- 一篇文章完成后，再处理下一篇文章
- 每篇文章都必须单独输出完整的固定格式
- 不要把多篇文章压缩成编号列表、要点列表或总览列表
- 不要省略“标题 / 链接 / 摘要 / CSS建议”这四个字段名
- 输出字段名统一使用半角冒号格式：`标题:` `链接:` `摘要:` `CSS建议:`

## 严格输出格式

我需要你总结每一篇文章，每篇文章必须严格按下面格式输出：

### 输出格式的例子

```markdown

# Extracting Insights from Video using OCI Generative AI

**链接：**  
https://blogs.oracle.com/developers/extracting-insights-from-video-using-oci-generative-ai

## 摘要

这篇文章实际介绍的内容，是一个**全运行在 Oracle Autonomous AI Database / Oracle AI Database 26ai 内部的“自主反欺诈流水线”**。它要解决的，不是传统规则引擎擅长的“单笔异常交易识别”问题，而是更复杂的**欺诈团伙识别**问题。所谓欺诈团伙，是指一组由同一攻击者控制、共享 IP、设备指纹或行为模式的账户。文章的核心价值，在于展示 Oracle 数据库平台已经能够把向量检索、图分析、自然语言转 SQL、Agent 编排和 MCP 工具暴露等能力全部收敛到同一数据库内部运行，不再依赖外部向量库、图数据库或独立 Agent 平台。

整个方案分为五层。

### 1. 向量检索

第一层是**向量检索**。作者把本地 ONNX embedding 模型直接加载到数据库中，利用 `VECTOR_EMBEDDING` 为客服工单文本生成向量，并建立 HNSW 向量索引。这样，数据库可以直接对工单内容做语义搜索，不需要调用外部 embedding API，也不需要额外部署向量数据库。文章特别强调，语义检索效果的关键不只是模型本身大小，更重要的是数据集覆盖是否均衡、是否包含足够多的典型欺诈和异常场景。

### 2. SQL Property Graph 图分析

第二层是**SQL Property Graph 图分析**。作者将银行客户表中的共享 IP 关系建模成图，把“共享同一 IP 的客户”连接起来，再通过 `GRAPH_TABLE` 查询找出成员数达到一定规模的 IP 集群，也就是潜在的欺诈团伙。这样做的意义在于，不再局限于普通关系表的一跳查询，而是可以在数据库内部直接进行图遍历和模式匹配，无需引入额外图数据库。

### 3. Select AI Profiles

第三层是**Select AI Profiles**。作者定义了两个 profile：一个用于普通 NL2SQL，面向客户表和工单表；另一个专门增强了图查询能力，支持生成与 `GRAPH_TABLE` 相关的 SQL。这样一来，不同的 agent 可以分别承担结构化数据分析和图谱侦查任务，使数据库中的自然语言分析能力更贴近实际业务需求。

### 4. MCP 工具暴露

第四层是**MCP 工具暴露**。借助 ADB 内嵌的 MCP Server，数据库中的 PL/SQL 函数可以被注册成 MCP 工具，例如只读 SQL 执行、图查询、工单语义搜索、运行 agent team 等。这样，外部的 MCP Client 可以直接访问数据库内部封装好的能力，但核心逻辑、数据处理和执行控制仍然留在数据库内部。这是 Oracle 在数据库原生 AI 集成方面的一个重要亮点。

### 5. 自主多 Agent 编排

第五层是**自主多 Agent 编排**。作者构建了两个 team：  
一个是“**被动调查型**”，输入某个客户 ID 后，系统会自动分析该客户的交易、工单、账户信息以及图上的关联成员；  
另一个是“**主动狩猎型**”，无需人工指定目标客户，系统会主动发现共享 IP 的可疑群组，并进一步自动生成案件报告，包括成员数量、风险类型、预估损失和建议动作，例如 `monitor`、`investigate`、`freeze`。

整体来看，这篇文章真正展示的，不只是一个反欺诈案例，而是 Oracle Autonomous AI Database / Oracle AI Database 26ai 作为**数据库内生 AI 平台**的能力：既能处理文本语义，又能处理关系网络，还能通过 Agent 和 MCP 形成自动化分析闭环。这种模式未来不仅可用于银行反欺诈，也可扩展到保险理赔风控、电信异常账户识别、零售会员欺诈、客服问题聚类、安全事件分析等场景。

## CSS建议
**CSS 可以介入，但应把它定位为“Oracle AI Database / Autonomous AI Database 能力落地咨询与场景化 PoC 服务”，而不是直接包装成成熟反欺诈产品服务。**
更合适的做法，是围绕数据库内 AI 能力形成一套可复制的标准交付框架，包括：
1. **客户场景筛选与成熟度评估**  
2. **场景化 PoC 验证**  
3. **分阶段扩展交付内容**  
这样做的好处是，一方面能够突出 Oracle 在数据库原生 AI 能力上的差异化价值，另一方面也能把交付风险控制在 CSS 可接受范围内，提升可售卖性、可复制性和标准化程度。
```

## 摘要要求

- 摘要必须尽量详细
- 摘要长度至少 300 个中文字以上
- 摘要不能只写一句话或几个要点
- 摘要应覆盖：
  - 文章主要解决的问题
  - 方案或架构的核心思路
  - 使用到的 Oracle 产品、服务、技术能力
  - 作者展示的实现方式、关键步骤或亮点
  - 该方案可能的实际应用场景

## CSS建议要求
what is CSS?
Oracle delivers fully integrated technology and AI solutions spanning infrastructure and applications across every industry we serve, constantly raising the bar on what’s possible. But today’s organizations need more than just great technology to achieve lasting business outcomes.
For sustained growth and a competitive industry advantage, customers rely on Oracle Customer Success Services (CSS) for end-to-end expertise across their Oracle ecosystem. The customer-centric approach, integration with Oracle Product Development, and collaboration with partners that CSS provides helps organizations accelerate solution adoption, foster innovation, and obtain long-term value from their Oracle investments.

- `CSS建议:` 后必须单独成段输出
- 不要只给一个简单结论
- 必须结合 CSS 交付、可售卖性、可复制性、客户价值、实施复杂度、交付风险来分析
- 需要明确说明：
  - 是否适合发展为 CSS 服务
  - 为什么适合或不适合
  - 适合什么类型客户
  - 是否容易形成标准化交付内容

# CSS 建议原则

判断重点：这个技术方案是否适合发展成 CSS 可交付、可售卖、可复制推广的服务内容。

请严格从 CSS 服务交付视角分析，而不是只从技术先进性角度评价。

重点考虑：

- 是否有明确客户价值
- 是否可复制、可标准化、可形成方法论
- 是否与 Oracle 现有产品、平台、最佳实践强相关
- 是否适合 assessment、migration、optimization、integration、security hardening、HA/DR、AI 落地、运维治理等 CSS 常见交付形态
- 如何需要开发技能，CSS比较适配APEX,PL/SQL,PYTHON, JAVA等技术,尤其是inside database的技术

## CSS 适配度结论

总判断只能选择以下之一：

- 非常适合 CSS 服务
- 比较适合 CSS 服务
- 部分适合 CSS 服务
- 不太适合 CSS 服务

并给出一句话总结原因。

## 适合哪些客户

建议同时说明：

- 行业类型
- 客户成熟度
- 是否适合大型企业或中型客户
- 是否适合已有 Oracle 技术栈客户
- 是否适合云转型客户
- 是否适合 AI 转型客户


