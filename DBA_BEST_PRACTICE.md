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

#### 创建 SSH Private Key 并配置免密登录

在 Windows 本地生成 key

在 CMD 中执行：

```cmd
cd /d E:\OpenSSH-Win64

E:\OpenSSH-Win64\ssh-keygen.exe -t ed25519 -f E:\OpenSSH-Win64\linux118.key -C "oracle@192.168.56.118"
```

如果不想输入 passphrase，连续回车两次即可。

生成后会得到两个文件：

```text
E:\OpenSSH-Win64\linux118.key       -- private key，本地保留
E:\OpenSSH-Win64\linux118.key.pub   -- public key，需要放到 Linux
```

#### 将 public key 写入 Linux 的 authorized_keys

在 CMD 中执行：

```cmd
type E:\OpenSSH-Win64\linux118.key.pub | E:\OpenSSH-Win64\ssh.exe oracle@192.168.56.118 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

第一次连接时，如果提示：

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入：

```text
yes
```

然后输入 Linux 上 oracle 用户的密码。

#### 测试 private key 登录

```cmd
E:\OpenSSH-Win64\ssh.exe -i E:\OpenSSH-Win64\linux118.key oracle@192.168.56.118
```

以后可以使用：

```cmd
ssh -i E:\OpenSSH-Win64\linux118.key oracle@192.168.56.118
```

---

#### 给 oracle 用户配置 sudo su - 权限

需要先用 root 用户登录 Linux。

#### 创建 sudoers 配置文件

```bash
su -

cat > /etc/sudoers.d/oracle <<'EOF'
oracle ALL=(ALL) NOPASSWD: ALL
EOF

chmod 440 /etc/sudoers.d/oracle
visudo -cf /etc/sudoers.d/oracle
```

如果输出类似下面内容，说明配置正确：

```text
/etc/sudoers.d/oracle: parsed OK
```

#### 测试 oracle 用户 sudo 权限

```bash
su - oracle
sudo su -
whoami
```

如果输出：

```text
root
```

说明配置成功。


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

做为一个DBA，你现在已经完成两个关键步骤

1. 可以用win ssh tool连接到linux，运行任意命令
2. 可以用oracle sqlcl MCP server连接到数据库，运行命令

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
