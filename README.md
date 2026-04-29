# Nanoorabot - AI System Agent

**本项目是一个基于 `nanobot` 与 `nanobot-webui` 二次开发的 AI System Agent 机器人系统，目标是构建一个能够长期运行、具备自主执行能力的智能系统管理员。**
*This project is an AI System Agent robot system developed based on `nanobot` and `nanobot-webui`, aiming to build an intelligent system administrator capable of long-term operation and autonomous execution.*
<img width="1258" height="225" alt="image" src="https://github.com/user-attachments/assets/8a2d39b9-a670-4660-9a3d-7d799076a824" />

*本项目由资深DBA系统架构师创建和维护，依赖vibe coding 进行开发和维护。欢迎大家一起vide coding。
*This project is created and maintained by a senior DBA system architect, with development powered by vibe coding. Everyone is welcome to join in and do vibe coding together.

**它面向主机管理、数据库管理和自动化运维场景，强调可扩展、可观测、可持续运行。**
*It targets host management, database management, and automated operations and maintenance (O&M) scenarios, emphasizing scalability, observability, and sustainable operation.*

**特别是针对 Oracle 数据库的运维，本系统提供了深度的自动化管理、故障排查与诊断能力。**
*Especially for Oracle database O&M, this system provides deep automated management, troubleshooting, and diagnostic capabilities.*

**系统特别引入了Oracle 26ai 的向量库能力作为知识库，大幅增强了专业知识的检索准确度。**
*The system specifically introduces the vector database capabilities of Oracle 26ai as its knowledge base MCP Server, significantly enhancing the retrieval accuracy professional knowledge.*

**系统采用Oracle MCP Server作为Oracle数据库的访问工具**
*The system specifically introduces Oracle MCP Server to access Oracle database.*

**通过整合 AI、工具 (Tool)、记忆 (Memory) 与 Web UI 的架构，我们形成了一个可落地的 Agent 管理平台，但本项目在开发中，仅仅限于用于DEV或者UAT环境，如果用于生产环境，后果自负，本项目不承担任何责任。。**
*By integrating the architecture of AI, Tools, Memory, and Web UI, we have formed a practical Agent management platform. This project is currently under development and is only intended for use in the DEV/UAT environment. If it is used in the production environment, the user shall bear all the consequences.This project assumes no responsibility.*
**目前本项目仅仅测试了KIMI和Deepseek API*
**Currently we just tested with KIMI and Deepseek API*

<img width="2240" height="1030" alt="image" src="https://github.com/user-attachments/assets/1aadb792-e618-4c17-9237-6f4c5eb3c01b" />

## 安装文档 | Installation guide
https://github.com/valenwong-exa/nanoorabot/blob/main/INSTALL.md
https://github.com/valenwong-exa/nanoorabot/blob/main/nanoorabot_linux_install.md
## DBA起步手册 | Beginning Guide for DBA
https://github.com/valenwong-exa/nanoorabot/blob/main/DBA_BEST_PRACTICE.md
## 核心特性 / Core Features

* **自主运行的系统管理员 / Autonomous System Administrator**: 
  **能够理解自然语言指令并将其转化为实际的运维操作。**
  *Capable of understanding natural language commands and translating them into actual O&M operations.*
* **Oracle 数据库深度运维 / Deep Oracle Database O&M**: 
  **内置针对 Oracle 数据库的专属管理技能，实现高效的日常维护与异常处理。**
  *Built-in exclusive management skills for Oracle databases to achieve efficient daily maintenance and exception handling.*
* **26ai 向量知识库 / 26ai Vector Knowledge Base**: 
  **依托 26ai 向量库构建强大的专业领域知识库，赋予 AI 准确的行业经验参考。**
  *Relying on the 26ai vector database to build a powerful professional domain knowledge base, endowing AI with accurate industry experience references.*
* **双轨记忆机制 / Dual-track Memory Mechanism**: 
  **支持灵活的短期会话记忆与长期的历史经验积累，支持通过 `/forget-session` 等显式指令进行灵活的记忆管理。**
  *Supports flexible short-term session memory and long-term historical experience accumulation, and supports flexible memory management through explicit commands such as `/forget-session`.*

## 基于项目 / Based On

**本项目的基础能力得益于以下优秀的开源项目：**
*The foundational capabilities of this project benefit from the following excellent open-source projects:*
<img width="862" height="171" alt="image" src="https://github.com/user-attachments/assets/91743b2a-474b-47e2-b0a8-dc6e85a2f1e7" />

* [nanobot](https://github.com/frostming/nanobot)
* [nanobot-webui](https://github.com/frostming/nanobot-webui)

## 内置第一个AI系统管理员 Danny | Buildin the first AI system administrator Danny

<img width="2285" height="778" alt="image" src="https://github.com/user-attachments/assets/47aa3a7c-0932-44ce-936f-5fe3003d96ca" />


## 主要的 系统管理员 特性 | Key Features for SYSTEM Admin

### 删除记忆 | Memory Deletion Commands Summary
* 因为运维机器人可能不需要记忆 Because OPS robot may not needs memory

### 推荐场景 | Recommended Scenarios

- 想让 AI 忘掉这次聊天上下文：`/forget-session`  
  Want the AI to forget the context of this chat: `/forget-session`

- 想把沉淀下来的长期记忆也一起清空：`/forget-history`  
  Want to clear accumulated long-term memory as well: `/forget-history`

- 想彻底重置：`/forget-all`  
  Want a full reset: `/forget-all`

  自然语言也可以工作| Nautal language works as well

- 只忘当前聊天：`forget current memory`  
- 只忘长期历史：`忘记历史记忆`  
- 全忘：`忘记所有记忆`  

## 可管理主机和数据库列表 | Server Host and Database list

<img width="2308" height="892" alt="image" src="https://github.com/user-attachments/assets/7b117288-e4c2-490d-89a1-cef99e613786" />

## AI交付记录审计存储在26ai数据库

## 数据库和主机危险命令防御

## 内置Oracle SkiLL

来自AI Data Flatform 团队整理

感谢整理和提供
```
https://github.com/oracle/skills
https://github.com/krisrice/oracle-db-skills
```



## DBA routine work SOP

## 基于Oracle 26ai的RAG文档维护和向量搜索功能

## 连接Oracle MCP Server

## 许可证 / License

**本项目采用 MIT 许可证开源。**
*This project is open-sourced under the MIT License.*

**请保留Valen Wang（王探长），Wanbin，Lijie 和AI Database Plaftform Team的署名 Please retain the bylines of Valen Wang and the AI Database Platform Team.*

**任何人都可以免费获取本软件及其相关文档的副本，并在满足 MIT 协议条款的前提下进行使用、复制、修改、合并、发布、分发等操作。**
*Anyone can obtain a copy of this software and its associated documentation files for free, and use, copy, modify, merge, publish, distribute, etc., under the terms of the MIT License.*
