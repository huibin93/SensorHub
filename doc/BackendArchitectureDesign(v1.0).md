# SensorHub 后端架构设计文档 (v1.0)

**文档状态**: 草稿 (Draft)  
**最后更新**: 2026-01-24  
**技术栈**: Python 3.10+, FastAPI, SQLModel (SQLAlchemy), Pandas, PyArrow

---

## 1. 概述 (Overview)

SensorHub 是一个用于管理、解析和分析大规模传感器数据的平台;后端系统面临的主要挑战是处理非结构化的大体积原始数据(ASCII Raw Data)与半结构化的分析数据(Pandas DataFrames)之间的转换与存储;

### 1.1 核心设计原则

*   **服务层模式 (Service Layer Pattern)**：将业务逻辑(解析、IO、打包)与 API 路由层严格分离;
*   **混合存储架构**：元数据存入关系型数据库 (SQLite/PostgreSQL);大数据存入文件系统 (Local/S3),采用 Parquet 列式存储以优化读取性能;
*   **基于角色的权限控制 (RBAC)**：通过 JWT 实现 Admin/Researcher/Viewer 分级授权;

---

## 2. 系统架构 (System Architecture)

### 2.1 逻辑分层

```mermaid
graph TD
    Client[前端 Vue] --> API[API 路由层 (FastAPI)]
    API --> Auth[鉴权中间件 (JWT)]
    API --> Service[Service 业务层]
    
    subgraph Services
    Service --> StorageSvc[存储服务 (I/O)]
    Service --> ParserSvc[解析服务 (Pandas)]
    Service --> ExportSvc[导出服务 (Zip流)]
    end
    
    Service --> Model[ORM 模型 (SQLModel)]
    Model --> DB[(SQL 数据库)]
    StorageSvc --> FS[(文件系统 /raw, /processed)]
```

### 2.2 目录结构规范

```plaintext
backend/
├── app/
│   ├── main.py                # 应用入口
│   ├── api/
│   │   ├── deps.py            # 依赖注入 (CurrentUser, DB Session)
│   │   └── v1/endpoints/      # 路由定义 (files.py, auth.py)
│   ├── core/
│   │   ├── config.py          # 环境变量配置
│   │   └── security.py        # JWT 加密解密逻辑
│   ├── models/                # 数据库模型 (SQLModel)
│   ├── schemas/               # Pydantic 数据验证 (DTO)
│   └── services/              # 核心业务逻辑
│       ├── storage.py         # 物理文件读写
│       ├── parser.py          # 原始数据解析算法
│       └── exporter.py        # 批量下载打包逻辑
└── storage/                   # 数据存储根目录 (git ignore)
    ├── raw/                   # 原始压缩包 (.gz)
    └── processed/             # 解析后的 Parquet 文件夹
```

---

## 3. 数据库设计 (Database Design)

### 3.1 实体关系图 (ERD 简述)

*   **User**: 存储用户信息及角色;
*   **SensorFile**: 存储文件元数据、状态及 JSON 结构摘要;
*   **Relationship**: User (1) -> (N) SensorFile (上传者关联,可选);

### 3.2 核心模型定义

#### 3.2.1 users 表

| 字段名 | 类型 | 索引 | 说明 |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | 用户唯一标识 |
| username | String | Unique | 登录名 |
| role | String | - | 权限角色: admin, researcher, viewer |
| hashed_password | String | - | 加密存储 |

#### 3.2.2 sensor_files 表

| 字段名 | 类型 | 索引 | 说明 |
| :--- | :--- | :--- | :--- |
| id | UUID | PK | 文件唯一标识 (用于文件系统映射) |
| filename | String | Yes | 原始文件名 |
| status | String | - | status: uploaded, parsing, ready, failed |
| raw_path | String | - | 原始文件相对路径 (e.g., `raw/uuid.raw.gz`) |
| processed_dir | String | - | 解析数据目录 (e.g., `processed/uuid/`) |
| content_meta | JSON | - | **关键设计**：存储解析后的数据结构摘要 |
| device_type | String | Yes | 业务字段 |

### 3.3 JSON 元数据结构 (content_meta)

此字段解决了“一个文件解析出多个不确定 DataFrame”的问题;

```json
{
  "summary": { "total_rows": 15000, "size_kb": 2048 },
  "keys": {
    "IMU_Data": { "rows": 10000, "columns": ["ax", "ay", "az"], "path": "IMU.parquet" },
    "GPS_Data": { "rows": 500, "columns": ["lat", "lon"], "path": "GPS.parquet" }
  }
}
```

---

## 4. 存储策略 (Storage Strategy)

### 4.1 原始数据 (Raw Data)

*   **格式**: `.raw.gz` (Gzip 压缩)
*   **位置**: `/storage/raw/{file_id}.raw.gz`
*   **理由**: ASCII 文本压缩率极高,Python gzip 模块可直接流式读取,无需解压到磁盘;

### 4.2 解析后数据 (Processed Data)

*   **格式**: `.parquet` (Snappy 或 Zstd 压缩)
*   **位置**: `/storage/processed/{file_id}/{key}.parquet`
*   **结构**: 每个 DataFrame 存为一个独立文件,文件夹以 File ID 命名;
*   **理由**:
    *   **按需读取**: 前端画图时只读取 GPS 数据,无需加载巨大的 IMU 数据;
    *   **Schema 保留**: 完美保留 float/int/datetime 类型,无需像 CSV 那样重复解析;

---

## 5. 接口定义 (API Specification)

所有接口前缀: `/api/v1`

### 5.1 认证 (Auth)

*   `POST /login/access-token`: 获取 JWT Token;

### 5.2 文件管理 (Files)

| 方法 | 路径 | 权限要求 | 描述 |
| :--- | :--- | :--- | :--- |
| POST | `/files/upload` | Researcher+ | 上传文件,保存为 gz,写入 DB,(可选) 触发异步解析; |
| GET | `/files` | Viewer+ | 分页获取文件列表;不返回 content_meta 以优化性能; |
| GET | `/files/{id}/structure` | Viewer+ | 获取单个文件的 content_meta JSON,用于展示文件包含哪些数据表; |
| PATCH | `/files/{id}` | Researcher+ | 修改备注、设备类型; |
| DELETE | `/files/{id}` | Admin | 物理删除文件及数据库记录; |

### 5.3 数据交互 (Data & Export)

| 方法 | 路径 | 权限要求 | 描述 |
| :--- | :--- | :--- | :--- |
| GET | `/files/{id}/data/{key}` | Viewer+ | 读取指定 Parquet 文件 (如 'IMU'),返回 JSON/Arrow 流供前端绘图; |
| GET | `/files/{id}/download` | Researcher+ | 流式下载单个 ZIP (含 raw + csv); |
| POST | `/files/batch-download` | Researcher+ | 批量下载;接收 ID 列表,流式返回大 ZIP 包; |

---

## 6. 核心业务流程 (Service Logic)

### 6.1 上传与解析流程

1.  **StorageService**: 接收 UploadFile -> 计算 Hash (去重) -> Gzip 压缩 -> 写入 `/raw` -> 返回路径;
2.  **DB**: 创建 SensorFile 记录,状态设为 `parsing`;
3.  **ParserService**:
    *   读取 `.raw.gz`;
    *   运行 Pandas 解析算法,得到 `Dict[str, DataFrame]`;
    *   遍历 Dict,将每个 DF 存为 Parquet 至 `/processed/{uuid}/`;
    *   生成 `content_meta` 统计信息;
4.  **DB**: 更新 `content_meta`,状态设为 `ready`;

### 6.2 批量下载流程 (Batch Download)

为防止内存溢出,必须使用生成器模式：

```python
def generate_zip_stream(file_ids):
    buffer = BytesIO()
    with ZipFile(buffer, mode="w") as zf:
        for file_id in file_ids:
            # 1. 写入 Raw Data
            zf.write(raw_path, arcname=f"{filename}/raw.txt")
            
            # 2. 实时转换 Parquet -> CSV 并写入
            for key in keys:
                df = pd.read_parquet(parquet_path)
                csv_str = df.to_csv()
                zf.writestr(f"{filename}/{key}.csv", csv_str)
            
            # 3. Yield 内存片段
            yield buffer.getvalue()
            buffer.truncate(0)
            buffer.seek(0)
```

---

## 7. 权限控制 (Security)

### 7.1 角色定义

*   **Admin**: 系统维护;可执行 DELETE 操作,管理 User 表;
*   **Researcher**: 核心用户;可上传、编辑、下载数据;
*   **Viewer**: 访客/只读用户;仅可查看列表和图表;

> **Note**: 先默认所有用户都是Admin,后续再添加权限控制;