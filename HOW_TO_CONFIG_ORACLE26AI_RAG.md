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