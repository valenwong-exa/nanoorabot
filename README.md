# AI System Agent

**本项目是一个基于 `nanobot` 与 `nanobot-webui` 二次开发的 AI System Agent 机器人系统，目标是构建一个能够长期运行、具备自主执行能力的智能系统管理员。**
*This project is an AI System Agent robot system developed based on `nanobot` and `nanobot-webui`, aiming to build an intelligent system administrator capable of long-term operation and autonomous execution.*

**它面向主机管理、数据库管理和自动化运维场景，强调可扩展、可观测、可持续运行。**
*It targets host management, database management, and automated operations and maintenance (O&M) scenarios, emphasizing scalability, observability, and sustainable operation.*

**特别是针对 Oracle 数据库的运维，本系统提供了深度的自动化管理、故障排查与诊断能力。**
*Especially for Oracle database O&M, this system provides deep automated management, troubleshooting, and diagnostic capabilities.*

**系统特别引入了 26ai 的向量库能力作为知识库，大幅增强了长期记忆与专业知识的检索准确度。**
*The system specifically introduces the vector database capabilities of 26ai as its knowledge base, significantly enhancing the retrieval accuracy of long-term memory and professional knowledge.*

**通过整合 AI、工具 (Tool)、记忆 (Memory) 与 Web UI 的架构，我们形成了一个可落地的 Agent 管理平台。**
*By integrating the architecture of AI, Tools, Memory, and Web UI, we have formed a practical Agent management platform.*

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

* [nanobot](https://github.com/frostming/nanobot)
* [nanobot-webui](https://github.com/frostming/nanobot-webui)

## 许可证 / License

**本项目采用 MIT 许可证开源。**
*This project is open-sourced under the MIT License.*

**任何人都可以免费获取本软件及其相关文档的副本，并在满足 MIT 协议条款的前提下进行使用、复制、修改、合并、发布、分发等操作。**
*Anyone can obtain a copy of this software and its associated documentation files for free, and use, copy, modify, merge, publish, distribute, etc., under the terms of the MIT License.*
