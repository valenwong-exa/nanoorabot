---
name: locallinux-inventory
description: 当用户要求连接本地 Windows 平台可访问的 Linux 主机，或提到 19c、26free、26ee、26ai免费版、26ai企业版 等主机别名时，使用本 Skill。该 Skill 用于帮助 AI 根据主机别名自动匹配正确的 IP、SSH key 文件名、默认用户和提权方式，并生成适合在 Windows PowerShell / OpenSSH 环境中执行的连接命令。注意该SKILL用于连接数据库的服务器，并非用于连接数据库实例，除非用户明确要求先登录主机，再连接主机上的数据库实例。
metadata: {"nanobot":{"emoji":"🖥️","requires":{"bins":["ssh"]}}}
---

# Local Linux Hosts

本 Skill 用于指导 AI 在本地 Windows 平台上，通过 OpenSSH 正确连接到预定义的 Linux 主机。

## When to Use This Skill

当用户出现以下意图时使用本 Skill：

- 要求 AI 连接某台 Linux 主机
- 提到主机别名，如 `19cdb`、`19c`、`19ee`、`26free`、`26aifree`、`26ai免费版`、`26ee`、`26aiee`、`26ai企业版`
- 要求生成 SSH 连接命令
- 要求在某台预定义主机上执行命令
- 要求确认某个主机对应的 IP、key、默认用户

## Host Inventory

- 主机列表请读取位于和SKILL文件在同一目录的: `linux-inventory.json` 文件获得

## Instructions

1. 当用户提到主机名或别名时，先在linux-inventory.json文件的内容中，匹配主机。
2. 默认使用用户 `oracle` 连接。
3. 默认运行环境是 Windows，采用 `win_ssh_linux` 工具，并优先生成适用于 Windows PowerShell 的 OpenSSH 命令。
4. 如果用户只说别名，例如“连接到 19c”或“登录 26ee”，AI 必须自动解析到正确主机，不要再次追问 IP、key 或默认用户。
5. 如果用户说“连接主机 19c / 26free / 26ee”，默认返回最简可执行连接命令，例如 `hostname`、`date`。
6. ssh工具和key的详细路径，默认由工具`win_ssh_linux`提供，除非客户明确给出key或者工具的完整路径。
7. 若用户要求对主机批量执行命令，可以按主机清单逐台生成命令，但不要混淆 key 与 IP 的对应关系。
