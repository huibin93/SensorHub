# SensorHub 数据存储与处理架构设计文档 (v1.0)

---

## 1. 概述 (Overview)

SensorHub 旨在管理和分析大规模传感器数据;鉴于原始数据 (rawdata) 为大体积 ASCII 文本，且解析后的数据结构具有动态性(键值对形式的 DataFrame 组)，本方案采用 “数据库元数据索引 + 文件系统分层存储” 的混合架构;

### 核心设计目标

*   **高性能读取**：解析后的数据需满足毫秒级读取，支持部分加载(只读某一部分数据);
*   **低存储成本**：原始文本必须高压缩存储;
*   **结构灵活性**：支持不同类型文件解析出不同的数据表(如 IMU、GPS、Logs);
*   **可追溯性**：保留原始文件以便算法更新后重新解析;

---

## 2. 存储架构设计 (Storage Architecture)

系统采用 UUID 作为唯一索引，文件系统物理路径与数据库记录解耦;

### 2.1 目录结构

```plaintext
/sensorhub_root
  ├── /database
  │     └── sensorhub.db          # SQLite 数据库
  │
  └── /storage                    # 物理文件存储区
        ├── /raw                  # 【原始数据区】
        │     ├── a1b2-c3d4.raw.gz    # Gzip 压缩的原始 ASCII 文件
        │     └── ...
        │
        └── /processed            # 【解析数据区】
              └── a1b2-c3d4/      # 以 UUID 命名的文件夹(对应一个文件包)
                    ├── IMU.parquet   # 解析出的子表 1 (二进制列式存储)
                    ├── GPS.parquet   # 解析出的子表 2
                    └── Event.parquet # 解析出的子表 3
```

### 2.2 文件格式选型

| 数据阶段 | 选型格式 | 理由 |
| :--- | :--- | :--- |
| **Raw Data** | `.raw.gz` (Gzip) | Python gzip 模块原生支持，pandas 可直接读取压缩流，平衡了压缩率与通用性; |
| **Processed** | `.parquet` (Snappy/Zstd) | 数据分析领域的标准格式;列式存储，读取速度极快，保留数据类型(Schema)，体积仅为 CSV 的 1/10; |
| **Download** | `.zip` (Dynamic) | 内存中动态生成;包含原始数据的 .raw 和转换后的 .csv; |

---

## 3. 数据库设计 (Database Schema)

使用 SQLAlchemy / SQLModel 定义模型;核心在于引入 JSON 字段存储非结构化的数据摘要;

### 3.1 核心表：SensorFile

```python
from sqlmodel import SQLModel, Field, JSON
from typing import Optional, Dict
from datetime import datetime
import uuid

class SensorFile(SQLModel, table=True):
    # --- 基础信息 ---
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str = Field(index=True)      # 原始文件名 (e.g., "watch_test_01.txt")
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    
    # --- 状态管理 ---
    status: str = Field(default="uploaded") # uploaded, parsing, ready, failed
    
    # --- 物理路径 (相对路径) ---
    raw_path: str                          # e.g., "storage/raw/uuid.raw.gz"
    processed_dir: Optional[str] = None    # e.g., "storage/processed/uuid/"
    
    # --- 关键：内容元数据 (JSON) ---
    # 存储解析后包含哪些 DataFrame 及其形状
    content_meta: Optional[Dict] = Field(default={}, sa_type=JSON)
    
    # --- 业务标签 ---
    device_type: Optional[str] = None
    note: Optional[str] = None
```

### 3.2 content_meta JSON 结构规范

数据库不存具体数据，只存“数据的目录”;

```json
{
  "summary": {
    "total_rows": 120500,
    "file_size_kb": 2048
  },
  "keys": {
    "IMU_Data": {
      "rows": 120000,
      "columns": ["timestamp", "acc_x", "acc_y", "acc_z"],
      "preview": "storage/processed/{uuid}/IMU_Data.parquet"
    },
    "GPS_Data": {
      "rows": 500,
      "columns": ["timestamp", "lat", "lon", "alt"],
      "preview": "storage/processed/{uuid}/GPS_Data.parquet"
    }
  }
}
```

---

## 4. 处理流程详解 (Processing Pipeline)

### 阶段 1：上传与归档 (Upload)

1.  前端分片上传文件;
2.  后端接收流，计算 MD5(查重用)，同时写入 `/storage/raw/{uuid}.raw.gz`;
3.  **Database**: 插入一条记录，Status=`uploaded`，记录 `raw_path`;

### 阶段 2：异步解析 (Parsing)

> 建议使用后台任务 (BackgroundTasks) 或 Celery 处理

1.  **Read**: 读取 `.raw.gz` 解压为文本流;
2.  **Parse**: 调用算法将文本转换为 Python 字典: `Dict[str, pd.DataFrame]`;
3.  **Write Parquet**:
    *   创建目录 `/storage/processed/{uuid}/`;
    *   遍历字典，将每个 DataFrame 保存为 `{Key}.parquet`;
4.  **Extract Meta**: 统计每个 DataFrame 的行数、列名;
5.  **Commit**:
    *   更新数据库 `content_meta` 字段;
    *   更新 `processed_dir` 路径;
    *   设置 Status=`ready`;

### 阶段 3：数据读取 (Reading)

*   **列表页**: 仅查询 SQLite，直接返回 JSON 中的 `content_meta` 供前端展示(如：“此文件包含 IMU 和 GPS 数据”);
*   **详情页/绘图**:
    *   前端请求 `GET /api/files/{id}/data?key=IMU_Data`;
    *   后端拼接路径 -> 读取对应的 `.parquet` -> 转换为 JSON/Arrow 流返回前端;
    *   **优势**：无需加载整个文件，只加载需要的列;

### 阶段 4：下载导出 (Exporting)

1.  用户请求下载;
2.  后端使用 `zipfile` 在内存中构建 ZIP 包;
3.  将 `/storage/raw` 中的原始文件写入 ZIP;
4.  (可选) 将 `/storage/processed` 中的 Parquet 转为 CSV 写入 ZIP;
5.  返回 `StreamingResponse`;

---

## 5. 接口设计 (API Definition)

| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| POST | `/api/files/upload` | 上传 rawdata，返回 file_id |
| GET | `/api/files` | 获取文件列表(包含 content_meta 摘要) |
| GET | `/api/files/{id}/structure` | 获取该文件的详细结构(包含哪些 Key, Columns) |
| GET | `/api/files/{id}/data/{key}` | 获取指定 Key 的具体数据 (如仅获取 GPS 数据) |
| GET | `/api/files/{id}/download` | 流式下载打包好的 ZIP |

---

## 6. 扩展性考虑 (Scalability)

*   **从 SQLite 到 PostgreSQL**:
    *   目前的 SQLModel 设计完全兼容 PostgreSQL;当文件数超过 10 万级或需要多用户并发写入时，可无缝切换;
*   **从本地存储到 S3**:
    *   `raw_path` 和 `processed_dir` 目前指向本地路径;未来可以封装一个 `StorageService`，将路径改为 S3 的 Key (e.g., `s3://bucket/uuid...`)，应用层逻辑无需大改;
*   **大文件解析优化**:
    *   对于超大文件(>2GB)，解析过程可引入 Dask 或 Polars 替换 Pandas，利用流式处理降低内存占用;

---

## 文档使用建议

*   **前端开发**：参考 API 定义和 JSON 结构，设计动态展示数据内容的组件;
*   **后端开发**：依据数据库 Schema 创建 Pydantic 模型，先实现 Parquet 的读写工具类;