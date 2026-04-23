Oracle DBA 快速起步 / Best Start for Oracle DBA

### 中文

适合 Oracle DBA 的一个快速起步方式如下：

#### 1. 创建一个带 Oracle Database 的测试虚拟机

建议先创建一个包含 Oracle Database 的测试 VM，用于学习、验证和测试相关操作。  
这样可以节省大量环境准备和排障时间。

参考链接：  
`https://www.oracle.com/database/technologies/databaseappdev-vm.html`

#### 2. 下载并配置 openssh-win64

请先下载 `openssh-win64`，并解压到本地目录。

然后配置系统环境变量：

`OPENSSH_HOME`

其值应指向 `openssh-win64` 的解压目录。

#### 3. 配置 linux-inventory Skill

需要完成以下配置：

- 配置 private key
- 配置 `linux-inventory.json`
- 按照 `SKILL.md` 的说明完成相关配置

#### 4. 配置 Oracle MCP Server

参考官方文档：  
`https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html`

其中最重要的一步是使用 SQLcl 保存数据库连接，例如：

```sql
SQL> conn -save cline_mcp -savepwd User123/pass123@//databaseserver:1521/orcl
Name: cline_mcp
Connect String: //databaseserver:1521/orcl
User: User123
Password: ******
Connected.
SQL>
```

你可以参考 `sqlcl-conn` Skill 来完成数据库连接配置。

#### 5. 导入并测试更多 Oracle Database Skills

完成以上步骤后，就可以继续导入并测试更多 Oracle Database 相关的 Skills。

---

### English

A good quick-start path for an Oracle DBA is as follows:

#### 1. Create a test VM with Oracle Database

It is recommended to start with a test virtual machine that already includes Oracle Database.  
This is very useful for learning, validation, and testing, and can save a lot of setup and troubleshooting time.

Reference:  
`https://www.oracle.com/database/technologies/databaseappdev-vm.html`

#### 2. Download and configure openssh-win64

Download `openssh-win64` and unzip it to a local directory.

Then configure the following environment variable:

`OPENSSH_HOME`

Its value should point to the directory where `openssh-win64` was extracted.

#### 3. Configure the linux-inventory Skill

The following items need to be configured:

- Configure the private key
- Configure `linux-inventory.json`
- Read `SKILL.md` and complete the required setup

#### 4. Configure the Oracle MCP Server

Refer to the official documentation:  
`https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html`

The most important step is to save the database connection in SQLcl, for example:

```sql
SQL> conn -save cline_mcp -savepwd User123/pass123@//databaseserver:1521/orcl
Name: cline_mcp
Connect String: //databaseserver:1521/orcl
User: User123
Password: ******
Connected.
SQL>
```

You can also refer to the `sqlcl-conn` Skill for database connection setup.

#### 5. Import and test more Oracle Database Skills

After completing the steps above, you can start importing and testing more Oracle Database related Skills.
