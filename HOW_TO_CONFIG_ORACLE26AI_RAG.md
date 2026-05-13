# 安装和启动Oracle 16ai Vector Search API

项目：https://github.com/oracle/oracle-16ai-vector-search-api

阅读项目的文档进行安装。
注意模型目录是空的，需要自己去huggingface下载。

# 在runtime目录配置oracle_config.json

{
  "driver": "python-oracledb",
  "user": "valen",
  "password": "oracle",
  "host": "192.168.56.101",
  "port": 1521,
  "service_name": "aidemo_pdb",
  "dsn": "192.168.56.101:1521/aidemo_pdb",
  "connect_string": "valen/oracle@192.168.56.101:1521/aidemo_pdb",
  "updated_at": "2026-05-06T09:22:13+00:00"
}


在nanobot webui启动的时候新增参数指向该json文件
--oracle-config %ORACLE_CONFIG%

参考 start_webui_dba1.bat 文件

# 可以在页面配置和测试26ai
<img width="2286" height="1120" alt="image" src="https://github.com/user-attachments/assets/2d0dd62e-ebe1-407e-bbfb-0d424751eaae" />

# 在Vector Search页面就是刚才配置的26ai database
在API启动的情况下，就可以在这里进行vector search
<img width="2302" height="1267" alt="image" src="https://github.com/user-attachments/assets/a9edaaa2-0c2f-43cd-a04a-2ad0fe49f847" />

# 后续就可以在Agent的MCP tool中使用该RAG API了
- 稍后更新RAG MCP tools
