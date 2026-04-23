# linux-inventory

## 中文

WEBUI主机页面的数据构建依赖于以下文件中的内容：

`<workspace>/<mydba>/skills/linux-inventory/linux-inventory.json`

打开主机页面后，系统会根据该文件中的配置内容，检查主机和数据库是否处于运行状态。

在使用该 Skill 之前，请先下载并解压 `openssh-win64`，然后在系统环境变量中设置 `OPENSSH_HOME`，其值应为解压后的目录路径。

当前版本中，从 Windows 访问 Linux 默认使用 `openssh-win64`。

访问 Linux 主机时，默认通过 **private key** 方式进行连接，默认用户名为 `oracle`。  
请自行创建 private key，并在 `linux-inventory.json` 中更新对应配置。

`linux-inventory.json` 的初始内容需要手工维护和更新。

如果需要使用其他连接方式，请相应修改 `SKILL.md` 中的实现说明和配置要求。

---

## English

The WEBUI host page is built based on the content defined in:

`<workspace>/<mydba>/skills/linux-inventory/linux-inventory.json`

When the page is opened, the system uses this configuration to check whether the host and database are running.

Before using this Skill, please download and extract `openssh-win64`, and set the `OPENSSH_HOME` environment variable to the extracted directory.

At present, access from Windows to Linux is implemented by default through `openssh-win64`.

Linux access is performed using a **private key** by default, and the default username is `oracle`.  
Please create your own private key and update the related settings in `linux-inventory.json`.

The initial content of `linux-inventory.json` must be maintained and updated manually.

If you want to use another access method, please modify `SKILL.md` accordingly.