Oracle DBA 快速起步 / Best Start for Oracle DBA

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

目前Linux主机，默认oracle用户为数据库用户，默认的bash配置是/home/oracle/.bash_profile
改配置文件，并非用代码读取，是AI自行阅读，所以目前可以修改json架构。



#### 4. 配置 Oracle MCP Server


参考官方文档：  
`https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.4/sqcug/using-oracle-sqlcl-mcp-server.html`
Oracle MCP需要安装JDK，版本需要大于17

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

自然语言提问：帮我连接到cline_mcp数据库。

#### 4. 申请和配置好AI API Key

推荐使用deepseek V4， KIMI2.6，其它API未经仔细测试，需自行测试。
修改nanobot-runtime/config.json
填入key和默认的workspace位置
如果你需要配置社交媒体，按照nanobot的本体的README.txt进行配置。


#### 5. 导入并测试更多 Oracle Database Skills

做为一个DBA，你现在已经完成两个关键步骤

1. 可以用win ssh tool连接到linux，运行任意命令
2. 可以用oracle sqlcl MCP server连接到数据库，运行命令

完成以上步骤后，就可以继续导入并测试更多 Oracle Database 相关的 Skills。

---


