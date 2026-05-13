# Oracle Vector Search API 调用说明

本文档用于给外部系统接入 `oracle_vector_api.py` 服务时参考。  
该服务基于 `FastAPI`，监听单端口 `19000`，提供以下三类能力：

1. `health` 探活
2. 文档上传、切分、embedding、入库
3. 向量检索 + reranker 重排


## 1. 服务概览

### 1.1 服务文件

- API 主程序：
  - `oracle_vector_api.py`
- 启动脚本：
  - `start_oracle_vector_api.bat`
- Oracle 连接配置：
  - `oracle_config.json`


### 1.2 监听端口

- 默认端口：
  - `19000`

推荐单端口部署，而不是拆成两个端口。原因如下：

- 上传和搜索共用同一套模型
- 上传和搜索共用同一套 Oracle 连接配置
- 单服务部署、运维和排障更简单
- 接入方只需要维护一个服务地址


### 1.3 服务地址示例

- 本机：
  - `http://127.0.0.1:19000`
- 局域网：
  - `http://<服务器IP>:19000`


## 2. 服务启动

### 2.1 推荐启动方式

使用 bat 脚本启动：

```bat
start_oracle_vector_api.bat
```

该脚本会执行以下动作：

- 检查 `19000` 端口
- 如果有旧进程占用该端口，则先杀掉
- 使用当前目录 `.venv` 中的 Python 启动 API


### 2.2 手工启动方式

```powershell
.\.venv\Scripts\python -m uvicorn oracle_vector_api:app --host 0.0.0.0 --port 19000
```


### 2.3 启动成功标志

终端出现类似输出：

```text
INFO:     Uvicorn running on http://0.0.0.0:19000
```


## 3. Oracle 配置

服务会自动读取同目录下的 `oracle_config.json` 连接数据库。

当前配置格式如下：

```json
{
  "driver": "python-oracledb",
  "user": "valen",
  "password": "oracle",
  "host": "192.168.56.101",
  "port": 1521,
  "service_name": "aidemo_pdb",
  "dsn": "192.168.56.101:1521/aidemo_pdb",
  "connect_string": "valen/oracle@192.168.56.101:1521/aidemo_pdb"
}
```

支持以下两种配置方式：

1. 直接提供 `dsn`
2. 提供 `host + port + service_name`

如果两者都提供，优先使用 `dsn`


## 4. 支持的文档类型

当前支持：

- `pdf`
- `txt`

说明：

- `pdf` 会先做 PDF 文字抽取
- `txt` 会直接读取原文，不走 PDF 解析器

不支持的格式会返回错误。


## 5. 数据库存储说明

服务使用两张表：

### 5.1 文档主表

- 表名：
  - `LC_DEMO_DOCUMENTS`

主要字段：

- `doc_id`
- `document_name`
- `document_text`
- `document_type`
- `source_file`

说明：

- `document_text` 保存完整文档原文
- `document_name` 有唯一约束


### 5.2 分片表

- 表名：
  - `LC_DEMO_CHUNKS`

主要字段：

- `doc_id`
- `chunk_id`
- `chunk_tokens`
- `chunk_text`
- `embedding`
- `document_type`
- `source_file`

说明：

- 每个 chunk 对应一条记录
- `embedding` 存 `VECTOR(2048, FLOAT32)`
- `source_file` 只在 `chunk_id = 1` 时写入


### 5.3 重复上传行为

如果上传同名文档：

- 会先尝试插入文档主表
- 如果命中文档名唯一约束
- 则捕获异常
- 不重复写入数据库
- 返回 `inserted = false`

也就是说：

- 同一个 `document_name` 不会重复入库
- 如果需要重新入库，请更换文件名，或手工删除原记录后再上传


## 6. 探活接口

### 6.1 接口地址

- `GET /health`


### 6.2 请求示例

```bash
curl http://127.0.0.1:19000/health
```


### 6.3 返回示例

```json
{
  "status": "ok"
}
```


## 7. 上传接口

### 7.1 接口地址

- `POST /documents/upload`


### 7.2 接口说明

上传一个文档后，服务会执行：

1. 识别文件类型
2. 解析文档全文
3. 按指定参数切分
4. 用本地 embedding 模型生成向量
5. 将完整文本写入文档表
6. 将分片和向量写入分片表


### 7.3 请求类型

- `multipart/form-data`


### 7.4 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `file` | 文件 | 是 | 无 | 要上传的 `pdf` 或 `txt` 文件 |
| `chunk_size_tokens` | 整数 | 否 | `500` | 每个分片的 token 大小 |
| `chunk_overlap_tokens` | 整数 | 否 | `50` | 分片重叠 token 数 |
| `source_file` | 字符串 | 否 | `blog` | 只写入 `chunk_id = 1` |
| `document_type` | 字符串 | 否 | 自动识别 | 文档类型，默认取文件扩展名 |
| `instruction` | 字符串 | 否 | 内置默认值 | embedding instruction |
| `device` | 字符串 | 否 | `cuda` | 可选 `auto` / `cuda` / `cpu` |
| `docs_table` | 字符串 | 否 | `LC_DEMO_DOCUMENTS` | 文档主表名 |
| `chunks_table` | 字符串 | 否 | `LC_DEMO_CHUNKS` | 分片表名 |


### 7.5 curl 示例

```bash
curl -X POST "http://127.0.0.1:19000/documents/upload" \
  -F "file=@Assessing and Tuning Network Performance for Data Guard and RMAN (Doc ID 2064368.1).pdf" \
  -F "chunk_size_tokens=500" \
  -F "chunk_overlap_tokens=50" \
  -F "source_file=blog" \
  -F "device=cuda"
```


### 7.6 Python requests 示例

```python
import requests

url = "http://127.0.0.1:19000/documents/upload"

with open("test.txt", "rb") as handle:
    files = {
        "file": ("test.txt", handle, "text/plain"),
    }
    data = {
        "chunk_size_tokens": "500",
        "chunk_overlap_tokens": "50",
        "source_file": "blog",
        "device": "cuda",
    }
    response = requests.post(url, files=files, data=data, timeout=600)

print(response.status_code)
print(response.json())
```


### 7.7 成功返回结构

```json
{
  "document_name": "test.txt",
  "document_type": "txt",
  "doc_id": 24,
  "inserted": true,
  "parsed_chunk_count": 8,
  "inserted_chunk_count": 8,
  "full_text_length": 6918,
  "full_text_preview": "1. 不要直接暴露真实业务复杂模型，建立 AI Semantic Layer ..."
}
```


### 7.8 返回字段说明

| 字段名 | 类型 | 说明 |
|---|---|---|
| `document_name` | 字符串 | 文档名 |
| `document_type` | 字符串 | 文档类型 |
| `doc_id` | 整数 | Oracle 文档主键 |
| `inserted` | 布尔 | 是否实际插入文档表 |
| `parsed_chunk_count` | 整数 | 解析后总分片数 |
| `inserted_chunk_count` | 整数 | 实际插入的 chunk 数 |
| `full_text_length` | 整数 | 完整原文长度 |
| `full_text_preview` | 字符串 | 完整原文预览 |


### 7.9 重复上传返回示例

```json
{
  "document_name": "test.txt",
  "document_type": "txt",
  "doc_id": 24,
  "inserted": false,
  "parsed_chunk_count": 8,
  "inserted_chunk_count": 0,
  "full_text_length": 6918,
  "full_text_preview": "..."
}
```

说明：

- `inserted=false` 表示文档名已存在
- 当前不会覆盖旧文档


## 8. 检索接口

### 8.1 接口地址

- `POST /search`


### 8.2 接口说明

该接口执行以下流程：

1. 对用户 `prompt` 生成 query embedding
2. 在 Oracle 中按 chunk 做 vector search
3. 将召回 chunk 用 reranker 重新打分
4. 根据 `reranker_score` 过滤
5. 按 `return_mode` 聚合为最终结果


### 8.3 请求类型

- `application/json`


### 8.4 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `prompt` | 字符串 | 是 | 无 | 用户查询文本 |
| `top_k` | 整数 | 否 | `5` | 最终返回文档数 |
| `reranker_score` | 浮点数 | 否 | `0.0` | 只有分片分数大于等于该值才参与返回 |
| `return_mode` | 字符串 | 否 | `split` | 可选 `full` / `split` / `title` |
| `fetch_k` | 整数 | 否 | 自动 | Oracle 初始召回的 chunk 数 |
| `document_type` | 字符串 | 否 | 无 | 可按文档类型过滤，如 `pdf` 或 `txt` |
| `device` | 字符串 | 否 | `cuda` | 可选 `auto` / `cuda` / `cpu` |
| `reranker_instruction` | 字符串 | 否 | 内置默认值 | reranker instruction |
| `instruction` | 字符串 | 否 | 内置默认值 | query embedding instruction |


### 8.5 `return_mode` 解释

#### `full`

返回：

- `文档名 + 完整文档 txt`
- `score` 为该文档命中分片中的最高 rerank 分

适合场景：

- 下游系统要拿到完整原文再做后处理
- 做全文展示


#### `split`

返回：

- `文档名 + 该文档所有命中且分数达标的分片内容`
- 分片按 `chunk_id` 顺序拼接
- `score` 为该文档命中分片中的最高 rerank 分

适合场景：

- 只返回与问题相关的片段
- 用于 RAG 上下文拼接


#### `title`

返回：

- 只返回 `文档名`
- `score` 为该文档命中分片中的最高 rerank 分

适合场景：

- 只做文档级召回
- 做列表展示


### 8.6 返回结构

统一返回 `list`

每个元素结构如下：

```json
{
  "txt": "返回文本",
  "score": 0.804688
}
```


### 8.7 请求示例

#### title 模式

```json
{
  "prompt": "how to Tuning Network Performance for Data Guard",
  "top_k": 3,
  "reranker_score": 0.3,
  "return_mode": "title",
  "device": "cuda",
  "document_type": "pdf"
}
```


#### split 模式

```json
{
  "prompt": "how to Tuning Network Performance for Data Guard",
  "top_k": 2,
  "reranker_score": 0.3,
  "return_mode": "split",
  "device": "cuda",
  "document_type": "pdf"
}
```


#### full 模式

```json
{
  "prompt": "how to Tuning Network Performance for Data Guard",
  "top_k": 2,
  "reranker_score": 0.3,
  "return_mode": "full",
  "device": "cuda",
  "document_type": "pdf"
}
```


### 8.8 curl 示例

```bash
curl -X POST "http://127.0.0.1:19000/search" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"how to Tuning Network Performance for Data Guard\",\"top_k\":2,\"reranker_score\":0.3,\"return_mode\":\"title\",\"device\":\"cuda\",\"document_type\":\"pdf\"}"
```


### 8.9 Python requests 示例

```python
import requests
import json

url = "http://127.0.0.1:19000/search"

payload = {
    "prompt": "how to Tuning Network Performance for Data Guard",
    "top_k": 2,
    "reranker_score": 0.3,
    "return_mode": "split",
    "device": "cuda",
    "document_type": "pdf"
}

response = requests.post(url, json=payload, timeout=600)

print(response.status_code)
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
```


### 8.10 返回示例

#### title 模式返回示例

```json
[
  {
    "txt": "Assessing and Tuning Network Performance for Data Guard and RMAN (Doc ID 2064368.1).pdf",
    "score": 0.796875
  },
  {
    "txt": "Application Containers In Physical Standby Data Guard Environment (Doc ID 2545894.1).pdf",
    "score": 0.421875
  }
]
```


#### split 模式返回示例

```json
[
  {
    "txt": "Assessing and Tuning Network Performance for Data Guard and RMAN (Doc ID 2064368.1).pdf\n<相关分片按 chunk_id 拼接后的内容>",
    "score": 0.796875
  }
]
```


#### full 模式返回示例

```json
[
  {
    "txt": "Assessing and Tuning Network Performance for Data Guard and RMAN (Doc ID 2064368.1).pdf\n<完整文档 txt>",
    "score": 0.796875
  }
]
```


## 9. 评分规则说明

接口中返回的 `score` 不是 Oracle 的向量距离，而是：

- 先按 Oracle vector search 找到相关 chunk
- 再对这些 chunk 用本地 reranker 打分
- 以 reranker 分作为筛选和最终返回依据

一个文档如果命中了多个 chunk：

- 只要其中任意一个 chunk 的 reranker 分大于等于 `reranker_score`
- 该文档就会进入最终结果
- 返回的 `score` 取这些命中 chunk 中的最高分


## 10. 推荐参数

### 10.1 上传接口推荐

- `chunk_size_tokens = 500`
- `chunk_overlap_tokens = 50`
- `device = cuda`


### 10.2 检索接口推荐

一般场景：

- `top_k = 5`
- `reranker_score = 0.3`
- `return_mode = split`
- `device = cuda`

只做文档名召回：

- `return_mode = title`

需要下游拿完整原文：

- `return_mode = full`


## 11. 错误处理

接口出错时会返回 `HTTP 400`

返回格式类似：

```json
{
  "detail": "错误信息"
}
```

常见错误包括：

- 文件不存在或文件名为空
- 文件类型不支持
- 本地模型目录缺失
- Oracle 连接失败
- 数据库权限不足
- CUDA 环境不可用但强制指定 `cuda`


## 12. 性能说明

- 推荐使用 `cuda`
- 当前环境已验证可用：
  - `RTX 4060 Ti`
  - `torch 2.11.0+cu128`

CPU 也可运行，但会明显更慢，尤其是：

- embedding
- reranker


## 13. 已验证能力

当前已经实际验证通过：

- `GET /health`
- 上传 `txt`
- 上传另一份 `pdf`
- `search` 的 `title` 模式
- `search` 的 `split` 模式
- `search` 的 `full` 模式
- `cuda` 模式运行
- Oracle 入库和检索


## 14. 配套测试脚本

本目录已提供两个可直接运行的测试脚本：

### 14.1 上传测试

- 文件：
  - `test_api_upload.py`

示例：

```powershell
.\.venv\Scripts\python .\test_api_upload.py
```

指定文件：

```powershell
.\.venv\Scripts\python .\test_api_upload.py "e:\embeding_example_2026\Assessing and Tuning Network Performance for Data Guard and RMAN (Doc ID 2064368.1).pdf"
```


### 14.2 搜索测试

- 文件：
  - `test_api_search.py`

功能：

- 会依次测试 `full`
- `split`
- `title`

示例：

```powershell
.\.venv\Scripts\python .\test_api_search.py
```


## 15. 接入建议

### 15.1 对上传接口的建议

- 上传前先做文件大小控制
- 尽量保持文档名稳定且唯一
- 如果需要重传覆盖，建议先加一个删除接口，或先人工删除旧文档


### 15.2 对搜索接口的建议

- 文档列表页：
  - 用 `title`
- RAG 检索上下文：
  - 用 `split`
- 需要全文交给下游模型：
  - 用 `full`


### 15.3 对调用超时的建议

- 上传接口建议超时设置大一些，如 `600` 秒
- 检索接口建议超时设置大一些，如 `600` 秒
- 如果文档量持续增大，建议后续增加：
  - 异步入库
  - 队列机制
  - 后台任务状态查询


## 16. Swagger 文档

FastAPI 默认提供在线接口文档：

- Swagger UI：
  - `http://127.0.0.1:19000/docs`
- ReDoc：
  - `http://127.0.0.1:19000/redoc`

如果接入方希望先人工试调用，推荐直接打开 `/docs`

