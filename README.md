# Oracle SQL CODEX CLI - Database AI System Agent

**本项目的主要目标是一个帮助用户使用智能体进行数据库工作**
*This project is an AI System Agent robot system developed based on `nanobot` and `nanobot-webui`, aiming to build an intelligent system administrator capable of long-term operation and autonomous execution.*
<img width="2167" height="725" alt="logo-oracle-preview" src="https://github.com/user-attachments/assets/efee34c0-be95-4e7f-afb7-ea271c7b3b39" />
## 本项目的主要用户
<img width="2552" height="1316" alt="image" src="https://github.com/user-attachments/assets/75b85a5e-61c8-46f4-91ae-59f0a6a6bc09" />


### 应用开发者
PL/SQL,SQL业务逻辑的开发和维护。请先从框架入手，然后再逐步添加特定于应用程序的技能。 提供了 PL/SQL,SQL,JAVA等技术栈的指导：连接配置、驱动程序/方言选择、数据类型映射和推荐的连接模式。框架设置完成后，再根据实际需要，深入学习应用程序开发技能，例如 JSON、空间数据、文本或连接池等方面的细节。按此顺序操作可以避免不必要的试错——在进行自定义之前，先采用经过 Oracle 验证的方案。
### 人工智能工程师
特性技能引入了 Oracle 的原生 AI 构建模块——用于受控 NL2SQL 的 Select AI 和 AI Profiles，以及DBMS_VECTOR用于检索和 RAG 的 AI Vector Search/。
### 数据库管理员
内置数百个Oracle社区SKILLs，面向用户场景进行定制。权限设计、审计，危险命令防御和加密均已经提供，而不仅仅是一句口号。
### 迁移负责人
迁移技能有助于评估和转换；DevOps 技能则负责交付机制，例如模式变更工作流程、在线运维、基于版本的重新定义以及测试。一次加载一个SKILL可以避免异构环境成为千篇一律的通用建议。

<img width="6898" height="397" alt="image" src="https://github.com/user-attachments/assets/51eb88fe-aefd-42f3-bda6-b47988862b81" />


*本项目由资深DBA系统架构师创建和维护，依赖vibe coding 进行开发和维护。欢迎大家一起vide coding。
*This project is created and maintained by a senior DBA system architect, with development powered by vibe coding. Everyone is welcome to join in and do vibe coding together.

**我们的目标是创建一个便于Oracle数据库管理员，开发人员，数据分析员易于的使用数据库优先Agent。目前的目标是支持oracle数据库，未来扩展为多种数据库（包括中国信创数据库）。它面向主机管理、数据库管理和自动化运维场景，强调可扩展、可观测、可持续运行。 **
*Our goal is to create a database priority agent that is easy for Oracle database administrators, developers, and data analysts to use. The current goal is to support the Oracle database, and in the future, it will be expanded to support multiple databases (including the China Information Innovation database). This project was jointly created and maintained by colleagues from the EAST&WEST China team of the Oracle Customer Success Department. It targets host management, database management, and automated operations and maintenance (O&M) scenarios, emphasizing scalability, observability, and sustainable operation.*

**特别是针对 Oracle 数据库的运维，本系统提供了深度的自动化管理、故障排查与诊断能力。**
*Especially for Oracle database O&M, this system provides deep automated management, troubleshooting, and diagnostic capabilities.*

**系统特别引入了Oracle 26ai 的向量库能力作为知识库，大幅增强了专业知识的检索准确度。**
*The system specifically introduces the vector database capabilities of Oracle 26ai as its knowledge base MCP Server, significantly enhancing the retrieval accuracy professional knowledge.*

**系统采用Oracle MCP Server作为Oracle数据库的访问工具**
*The system specifically introduces Oracle MCP Server to access Oracle database.*

**通过整合 AI、工具 (Tool)、记忆 (Memory) 与 Web UI 的架构，我们形成了一个可落地的 Agent 管理平台，但本项目在开发中，仅仅限于用于DEV或者UAT环境，如果用于生产环境，后果自负，本项目不承担任何责任。。**
*By integrating the architecture of AI, Tools, Memory, and Web UI, we have formed a practical Agent management platform. This project is currently under development and is only intended for use in the DEV/UAT environment. If it is used in the production environment, the user shall bear all the consequences.This project assumes no responsibility.Author: Valen Wong
Oracle employee, working on Oracle Database Platfrom team of China CSS department.
This is a personal open-source project. It is not an official Oracle product, not sponsored by Oracle, and does not represent Oracle’s views.*
**目前本项目仅仅测试了KIMI和Deepseek API*
**Currently we just tested with KIMI and Deepseek API*

<img width="2240" height="1030" alt="image" src="https://github.com/user-attachments/assets/1aadb792-e618-4c17-9237-6f4c5eb3c01b" />

## 安装文档 | Installation guide

- [Windows](INSTALL.md)
- [macOS](INSTALL_mac.md)
- [OCI / Oracle Linux 8](INSTALL_oci_oraclelinux8.md)
- [可选语音功能 / Optional voice support](INSTALL_voice.md)

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

## 可管理主机和数据库列表 | Server Host and Database list

<img width="2308" height="892" alt="image" src="https://github.com/user-attachments/assets/7b117288-e4c2-490d-89a1-cef99e613786" />
Use Server list and database list to generate prompt to guide AI to connect to correct  target server or database
<img width="2271" height="1260" alt="image" src="https://github.com/user-attachments/assets/92bcdbef-1316-40f8-adce-143093eeb9fa" />

## 打开数据库metadata tree | Open Database metadata tree
提供一个类似数据库开发工具的界面 Provide an interface similar to a database development tool
<img width="2312" height="1296" alt="image" src="https://github.com/user-attachments/assets/75dfb49d-f9de-49ef-b8fe-8264e5f6aa5c" />
可执行Oracle数据库库对象分析，修改，创建，编译 Can perform analysis, modification, creation and compilation of Oracle database library objects
<img width="1348" height="1185" alt="image" src="https://github.com/user-attachments/assets/565177d1-76c0-4137-b428-53f809524367" />

<img width="326" height="534" alt="image" src="https://github.com/user-attachments/assets/86753da7-0c04-4da8-8c9d-692d8d5011c8" />
数据库快速检查 Database Quick Check
<img width="2296" height="1261" alt="image" src="https://github.com/user-attachments/assets/03085ed8-c139-4cdb-bafa-ba208213a5af" />


## 可选集成26ai数据库 | Integrate with Oracle 26ai（Optional）
<img width="2530" height="859" alt="image" src="https://github.com/user-attachments/assets/98e0dd97-929c-48fd-90d1-fa0bca685083" />

## 数据库和主机危险命令防御
<img width="2289" height="1129" alt="image" src="https://github.com/user-attachments/assets/6fe3bae9-bb6a-4401-98fc-49f1e81d6d61" />


## 基于Oracle 26ai的RAG文档维护和向量搜索功能 | Oracle 26ai Vector Search
Default use QWEN or BGE-M3 model , mutiple langguages support.
Using langchain.
Check RAG onboard document about how to config Oracle 26ai vector search
<img width="2318" height="1262" alt="image" src="https://github.com/user-attachments/assets/4d91caf2-2120-48e5-a2a3-2dbe397c05ac" />



## 连接Oracle MCP Server
<img width="2306" height="365" alt="image" src="https://github.com/user-attachments/assets/4de8a1cd-5ba1-4994-a22e-984c26e7f629" />


## 许可证 / License

**本项目采用 MIT 许可证开源。**
*This project is open-sourced under the MIT License.*

**请保留Valen Wang（王探长），Barry Wang，Lijie 和AI Database Plaftform Team的署名 Please retain the bylines of Valen Wang,Barry Wang, Sam Li and the AI Database Platform Team.*

**任何人都可以免费获取本软件及其相关文档的副本，并在满足 MIT 协议条款的前提下进行使用、复制、修改、合并、发布、分发等操作。**
*Anyone can obtain a copy of this software and its associated documentation files for free, and use, copy, modify, merge, publish, distribute, etc., under the terms of the MIT License.*
