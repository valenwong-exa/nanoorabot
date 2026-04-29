Oracle DBA 快速起步 / Best Start for Oracle DBA (EN version follows in the latter part.)

### 中文

适合 Oracle DBA 的一个快速起步方式如下：

#### 1. 创建一个带 Oracle Database 的测试虚拟机

建议先创建一个包含 Oracle Database 的测试 VM，用于学习、验证和测试相关操作。  
这样可以节省大量环境准备和排障时间。里面自带一个free26，但你可以轻松的卸载掉，安装任何>=19c版本。

参考链接：  
`https://www.oracle.com/database/technologies/databaseappdev-vm.html`

#### 2. 下载并配置 openssh-win64

请先下载 `openssh-win64`，并解压到本地目录。

然后配置系统环境变量：

`OPENSSH_HOME`

其值应指向 `openssh-win64` 的解压目录。

内置的ssh 工具，会默认调用它，访问Linux Server

#### 创建 SSH Private Key 并配置免密登录

内置ssh工具是用private key 来实现自动化访问Linux，并运行命令。所以，你要创建key。
类似我们使用云服务器，也是采用private key运维，方法同理。

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
```
    {
      "host_name": "MiWiFi-R3P-srv",
      "aliases": [
        "23ai",
        "23db"
      ],
      "ip": "192.168.56.118",
      "ssh_key": "E:\\OpenSSH-Win64\\linux118.key",
      "default_user": "oracle",
      "privilege_escalation": "sudo su -",
      "os_type": "Oracle Linux 8.10",
      "databases": [
        {
          "database_name": "ORCLCDB",
          "sqlcl_saveconnname": "orcldb",
          "database_version": "23.0.0.0.0",
          "oracle_home": "/opt/oracle/product/23c/dbhome_1",
          "pdb": "Y",
          "database_status": "OPEN"
        }
      ],
      "host_status": "Running"
    },
```

- 配置 private key
- 配置 `linux-inventory.json`
- 按照 `SKILL.md` 的说明完成相关配置,主机的IP，private key的位置，主机别名aliases（如果担心引起歧义，可以不写别名，但你需要精确的告诉AI主机名或者IP，数据库的信息，其中sqlcl_saveconnname 是在Oracle MCP server saved的CONNECTION NAME，用于连接数据库）

配置好以后，可以用自然语言：
帮我连接到23ai的Linux，检查下sysctl配置
帮我连接到orcldb的数据库，检查一下字符集
*注意：最好加上Linux 或者 数据库 在prompt中，否则AI很可能困惑，你是连接Linux还是数据库（采用ORACLE MCP工具）*
<img width="1113" height="807" alt="image" src="https://github.com/user-attachments/assets/cc3e2ccf-7e70-4279-8d6d-2a70c33c2aa8" />

目前Linux主机，默认oracle用户为数据库用户，默认的bash配置是/home/oracle/.bash_profile
AI读取配置文件，并非用代码读取，是AI自行阅读。但是Dashboard页面是解析该json，所以需要保持基本格式。但可以添加新items。
<img width="560" height="597" alt="image" src="https://github.com/user-attachments/assets/2ed34a05-5383-498a-9828-2dfb3f0ab188" />




#### 4. 配置 Oracle MCP Server


参考官方文档：  
`https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html`
Oracle MCP需要安装JDK，版本需要大于17

其中最重要的一步是使用 SQLcl 保存数据库连接，例如：

```sql
SQL> conn -save 19cdb -savepwd User123/pass123@//databaseserver:1521/orcl
Name: 19cdb
Connect String: //databaseserver:1521/orcl
User: User123
Password: ******
Connected.
SQL>
```
配置好以后，可以测试
```
sql -name 19cdb
```
在config.json的末尾配置,例如
```
"oracle-sqlcl": {
        "type": "stdio",
        "command": "E:\\sqlcl\\bin\\sql.exe",
        "args": [
          "-R",
          "0",
          "-mcp"
        ],
        "env": {},
        "url": "",
        "headers": {},
        "toolTimeout": 30,
        "enabledTools": [
          "*"
        ]
      },
```
配置好以后，在页面工具/MCP，可以看到工具已经生效。
<img width="1572" height="303" alt="image" src="https://github.com/user-attachments/assets/3e29c551-442e-4313-a673-8d368b94e016" />

自然语言提问：帮我连接到19cdb数据库。
<img width="1125" height="841" alt="image" src="https://github.com/user-attachments/assets/0347705b-0390-4e11-8c35-4617944d7621" />

在测试环境，MCP的安全级别为0，所以可以执行任何命令和脚本。具体可以阅读oracle的SQLCL guide
<img width="1070" height="529" alt="image" src="https://github.com/user-attachments/assets/1c23f5cd-fe3b-4184-9c4f-331fb5eaa129" />


#### 4. 申请和配置好AI API Key

推荐使用deepseek V4， KIMI2.6，其它API未经仔细测试，需自行测试。
修改nanobot-runtime/config.json
填入key和默认的workspace位置
如果你需要配置社交媒体，按照nanobot的本体的README.txt进行配置。


#### 5. 导入并测试更多 Oracle Database Skills

做为一个DBA，你现在已经完成两个关键步骤

1. 可以用win ssh tool连接到linux，运行任意命令
2. 可以用oracle sqlcl MCP server连接到数据库，运行命令

#### 6. 测试APPLY ONEOFF Patch 的简单说明

dba1中带有一个one off patch的SKILL
前提是
1. 你可以通过ssh连接到linux  就绪
2. Linux环境最好是标准和规范的oracle的环境，环境变量都设置完备。避免AI反复浪费tokens去搜索路径。

测试： 帮我在19cdb linux安装one off 补丁 23399134， 补丁在workspace的patch目录，包含 23399134 和 6880880，帮我上传到/oracle/patch，并进行安装工作。
PS：你可以提前帮AI上传好补丁，节约tokens。
具体步骤，阅读SKILL.md，按需进行修改。

#### END
完成以上步骤后，就可以继续导入并测试更多 Oracle Database 相关的 Skills。

---


# Best Start for Oracle DBA

A quick-start approach for Oracle DBAs is as follows:

## 1. Create a Test VM with Oracle Database

It is recommended to first create a test VM that already includes Oracle Database.  
This VM can be used for learning, validation, and testing DBA operations.

This can save a lot of time on environment preparation and troubleshooting.  
The VM comes with Oracle Database Free 26ai by default, but you can easily uninstall it and install any Oracle Database version >= 19c.

Reference:

`https://www.oracle.com/database/technologies/databaseappdev-vm.html`

---

## 2. Download and Configure openssh-win64

First, download `openssh-win64` and extract it to a local directory.

Then configure the system environment variable:

`OPENSSH_HOME`

The value should point to the directory where `openssh-win64` was extracted.

The built-in SSH tool will use this directory by default to access Linux servers.

---

## Create an SSH Private Key and Configure Passwordless Login

The built-in SSH tool uses a private key to automatically access Linux and run commands.  
Therefore, you need to create an SSH key.

This is similar to how we manage cloud servers using private keys.

### Generate the Key Locally on Windows

Run the following commands in CMD:

```cmd
cd /d E:\OpenSSH-Win64

E:\OpenSSH-Win64\ssh-keygen.exe -t ed25519 -f E:\OpenSSH-Win64\linux118.key -C "oracle@192.168.56.118"
```

If you do not want to set a passphrase, press Enter twice.

After the key is generated, you will get two files:

```text
E:\OpenSSH-Win64\linux118.key       -- private key, keep it locally
E:\OpenSSH-Win64\linux118.key.pub   -- public key, copy it to Linux
```

### Add the Public Key to Linux authorized_keys

Run the following command in CMD:

```cmd
type E:\OpenSSH-Win64\linux118.key.pub | E:\OpenSSH-Win64\ssh.exe oracle@192.168.56.118 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

When connecting for the first time, if you see the following prompt:

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Enter:

```text
yes
```

Then enter the password of the `oracle` user on Linux.

### Test Private Key Login

```cmd
E:\OpenSSH-Win64\ssh.exe -i E:\OpenSSH-Win64\linux118.key oracle@192.168.56.118
```

After that, you can use:

```cmd
ssh -i E:\OpenSSH-Win64\linux118.key oracle@192.168.56.118
```

---

## Configure sudo su - Privilege for the oracle User

First, log in to Linux as the `root` user.

### Create a sudoers Configuration File

```bash
su -

cat > /etc/sudoers.d/oracle <<'EOF2'
oracle ALL=(ALL) NOPASSWD: ALL
EOF2

chmod 440 /etc/sudoers.d/oracle
visudo -cf /etc/sudoers.d/oracle
```

If the output is similar to the following, the configuration is correct:

```text
/etc/sudoers.d/oracle: parsed OK
```

### Test sudo Privilege for the oracle User

```bash
su - oracle
sudo su -
whoami
```

If the output is:

```text
root
```

The configuration is successful.

---

## 3. Configure the linux-inventory Skill

You need to complete the following configuration:

```json
{
  "host_name": "MiWiFi-R3P-srv",
  "aliases": [
    "23ai",
    "23db"
  ],
  "ip": "192.168.56.118",
  "ssh_key": "E:\\OpenSSH-Win64\\linux118.key",
  "default_user": "oracle",
  "privilege_escalation": "sudo su -",
  "os_type": "Oracle Linux 8.10",
  "databases": [
    {
      "database_name": "ORCLCDB",
      "sqlcl_saveconnname": "orcldb",
      "database_version": "23.0.0.0.0",
      "oracle_home": "/opt/oracle/product/23c/dbhome_1",
      "pdb": "Y",
      "database_status": "OPEN"
    }
  ],
  "host_status": "Running"
}
```

You need to:

- Configure the private key
- Configure `linux-inventory.json`
- Follow the instructions in `SKILL.md` to complete the configuration

The configuration should include the host IP, private key path, host aliases, and database information.

If you are worried about ambiguity, you can choose not to define aliases.  
In that case, you need to tell the AI the exact host name or IP address.

For database information, `sqlcl_saveconnname` is the saved connection name configured in the Oracle MCP Server.  
It is used to connect to the database.

After the configuration is complete, you can use natural language such as:

```text
Connect to the Linux host 23ai and check the sysctl configuration.
```

```text
Connect to the orcldb database and check the character set.
```

Note:

It is better to explicitly mention either `Linux` or `database` in the prompt.  
Otherwise, the AI may become confused about whether it should connect to Linux or use the Oracle MCP tool to connect to the database.

Currently, the default Linux user is `oracle`, which is also the database OS user.  
The default bash configuration file is:

```text
/home/oracle/.bash_profile
```

The AI reads the configuration file by understanding the text, not by hard-coded parsing logic.  
However, the Dashboard page parses this JSON file, so the basic JSON format must be preserved.

You can add new items if needed.

---

## 4. Configure Oracle MCP Server

Reference official documentation:

`https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html`

Oracle MCP requires JDK, and the version must be greater than 17.

The most important step is to save the database connection using SQLcl, for example:

```sql
SQL> conn -save 19cdb -savepwd User123/pass123@//databaseserver:1521/orcl
Name: 19cdb
Connect String: //databaseserver:1521/orcl
User: User123
Password: ******
Connected.
SQL>
```

After configuration, you can test it with:

```bash
sql -name 19cdb
```

At the end of `config.json`, add a configuration similar to the following:

```json
"oracle-sqlcl": {
  "type": "stdio",
  "command": "E:\\sqlcl\\bin\\sql.exe",
  "args": [
    "-R",
    "0",
    "-mcp"
  ],
  "env": {},
  "url": "",
  "headers": {},
  "toolTimeout": 30,
  "enabledTools": [
    "*"
  ]
}
```

After the configuration is complete, you can check the Tools / MCP page.  
You should be able to see that the tool is enabled.

You can then ask in natural language:

```text
Connect to the 19cdb database.
```

In a test environment, the MCP security level is set to 0, so it can execute any command or script.  
For more details, refer to the Oracle SQLcl guide.

---

## 5. Apply for and Configure an AI API Key

It is recommended to use DeepSeek V4 or Kimi 2.6.

Other APIs have not been thoroughly tested, so you need to test them yourself.

Modify:

```text
nanobot-runtime/config.json
```

Fill in the API key and the default workspace location.

If you need to configure social media integration, follow the README file of the original Nanobot project.

---

## 6. Import and Test More Oracle Database Skills

As a DBA, you have now completed two key steps:

1. You can use the Windows SSH tool to connect to Linux and run commands.
2. You can use Oracle SQLcl MCP Server to connect to the database and run commands.

---

## 7. Simple Test for Applying a One-Off Patch

The `dba1` directory includes a one-off patch Skill.

Prerequisites:

1. You can connect to Linux through SSH.
2. The Linux environment should preferably be a standard and well-configured Oracle environment, with all environment variables properly set.

This avoids wasting tokens while the AI repeatedly searches for paths.

Example test prompt:

```text
Install one-off patch 23399134 on the 19cdb Linux host. 
The patch files are located in the workspace patch directory, including 23399134 and 6880880. 
Upload them to /oracle/patch and perform the installation.
```

PS:

You can upload the patch files in advance to save tokens.

For detailed steps, read `SKILL.md` and modify it as needed.

---

## END

After completing the above steps, you can continue importing and testing more Oracle Database-related Skills.


