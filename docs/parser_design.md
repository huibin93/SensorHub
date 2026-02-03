# 数据解析模块设计方案

## 1. 整体架构

```
backend/app/
├── services/
│   ├── parser.py          # 解析服务入口 (已有, 需修改)
│   └── storage.py         # 存储服务 (已有)
├── parsers/               # [新建] 解析脚本专用目录
│   ├── __init__.py
│   ├── rawdata_parser.py  # [用户提供] get_raw_data 函数 (数据解析)
│   └── metadata_parser.py # [用户提供] 元数据解析 (初步解析)
└── api/v1/endpoints/
    └── files.py           # 修改 trigger_parse 接口
```

---

## 2. 两阶段解析架构

### 阶段 1: 元数据解析 (用户手动触发)

- **触发时机**: 文件上传/导入完成后用户手动执行
- **目的**: 快速提取文件头部元信息，用于列表展示和过滤
- **输出**: 写入 `SensorFile.content_meta` 字段

```python
# parsers/metadata_parser.py
def parse_metadata(file_path: str, encoding: str = 'utf-8') -> dict:
    """
    快速解析文件头部元数据;
    
    Returns:
        {
            "is_ring": bool,           # 推断的设备类型
            "data_types": list,        # 包含的数据类型列表
            "estimated_duration": str, # 估算时长
            "error": str | None        # 解析错误信息 (如有)
        }
    """
```

### 阶段 2: 数据解析 (主动触发)

- **触发时机**: 用户点击 "Parse" 按钮
- **目的**: 完整解析所有传感器数据，生成 Parquet 文件
- **输出**: 写入 `storage/processed/{hash}/*.parquet`

```python
# parsers/rawdata_parser.py
def get_raw_data(file_path: str, encoding: str = 'utf-8', is_ring: bool = False) -> dict:
    """
    完整解析传感器数据;
    
    Returns:
        {
            "acc_df": pd.DataFrame,    # 仅存在时返回
            "gyro_df": pd.DataFrame,
            "ppg_g_df": pd.DataFrame,
            ...
            "error": str | None        # 解析错误信息 (如有)
        }
    """
```

---

## 3. is_ring 判断优先级

```
数据库 device_type == "Ring" ?
    │
    ├── YES ──▶ is_ring = True
    │
    └── NO ──▶ 从文件内容推断 (metadata_parser 返回)
              ├── 推断结果存在 ──▶ 使用推断值
              └── 推断失败 ──▶ 默认 is_ring = False (Watch)
```

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 数据库 `device_type` | 用户在前端明确设置 |
| 2 | 元数据解析推断 | 从文件头部特征判断 |
| 3 | 默认值 | `is_ring = False` (Watch) |

---

## 4. 数据流

```
[上传完成] ──▶ 阶段 1: 元数据解析 (自动)
    │
    ├─1─▶ StorageService.get_raw_path(hash) → 获取 .zst 文件路径
    ├─2─▶ 解压文件头部 (仅需前 N 行)
    ├─3─▶ parsers.metadata_parser.parse_metadata(temp_path)
    └─4─▶ 更新 DB: content_meta = {..., is_ring: ...}

[用户点击 Parse] ──▶ 阶段 2: 数据解析 (主动)
    │
    ├─1─▶ StorageService.get_raw_path(hash) → 获取 .zst 文件路径
    ├─2─▶ 解压完整文件到临时目录
    ├─3─▶ parsers.rawdata_parser.get_raw_data(temp_path, is_ring=...)
    │            │
    │            └── 返回 dict: {acc_df, gyro_df, ...} (动态 key)
    ├─4─▶ 每个 df 保存到 storage/processed/{hash}/*.parquet
    └─5─▶ 更新 DB: status="processed", content_meta={keys, summary...}
```

---

## 5. 输入/输出规范

### 5.1 元数据解析 (`parse_metadata`)

**输入:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `file_path` | `str` | 解压后的原始 rawdata 文件路径 |
| `encoding` | `str` | 文件编码, 默认 `utf-8` |

**输出:** (动态 key，不存在则不返回)
```python
{
    "is_ring": bool,           # 推断的设备类型
    "data_types": list,        # ["acc", "gyro", "ppg_g", ...]
    "estimated_duration": str, # "00:05:30"
    "error": str               # 仅在出错时返回此 key
}
```

### 5.2 数据解析 (`get_raw_data`)

**输入:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `file_path` | `str` | 解压后的原始 rawdata 文件路径 |
| `encoding` | `str` | 文件编码, 默认 `utf-8` |
| `is_ring` | `bool` | 是否为戒指设备 |

**输出:** (动态 key，不存在则不返回)
```python
{
    # 以下 key 仅在数据存在时返回
    "base_info_df": pd.DataFrame,     # 基础信息
    "wear_info_df": pd.DataFrame,     # 佩戴信息
    "acc_df": pd.DataFrame,           # 加速度
    "gyro_df": pd.DataFrame,          # 陀螺仪
    "ppg_g_df": pd.DataFrame,         # 绿光 PPG
    "ppg_r_df": pd.DataFrame,         # 红光 PPG
    "ppg_ir_df": pd.DataFrame,        # 红外 PPG
    "ppg_r_ir_df": pd.DataFrame,      # 红外红光 PPG
    "TYHX_data_df": pd.DataFrame,     # TYHX 数据
    "TYHX_agc_data_df": pd.DataFrame, # TYHX AGC
    "TYHX_3697_data_df": pd.DataFrame,# TYHX 3697 (戒指)
    "data_types": dict,               # 数据类型统计
    
    # 错误信息 (仅在出错时返回)
    "error": str
}
```

---

## 6. 错误处理规范

两阶段解析都采用 `error` 键传递错误信息:

```python
# 成功时
{"acc_df": ..., "gyro_df": ...}

# 失败时
{"error": "Failed to parse metadata: Invalid file format"}
```

> [!IMPORTANT]
> - 如果返回了 `error` 键，其他数据键可能缺失或不完整
> - 调用方需优先检查 `error` 键是否存在

---

## 7. Parquet 存储设计

### 保存位置

```
storage/processed/{file_hash}/
├── acc.parquet          # 加速度数据 (snappy 压缩)
├── gyro.parquet         # 陀螺仪
├── ppg_g.parquet        # 绿光 PPG
├── ppg_r.parquet        # 红光 PPG
├── ppg_ir.parquet       # 红外 PPG
├── ppg_r_ir.parquet     # 红外红光 PPG
├── base_info.parquet    # 基础信息
├── wear_info.parquet    # 佩戴信息
├── TYHX_data.parquet
├── TYHX_agc.parquet
├── TYHX_3697.parquet    # (仅戒指)
└── meta.json            # 统计信息 (data_types + 行数等)
```

### Parquet 优势

- 列式存储, 读取特定列时极快
- 内置 `snappy` 压缩 (低 CPU, 中等压缩率) 或 `zstd` (高压缩率)
- 与 Pandas/Polars/DuckDB 无缝集成

---

## 8. 分工明细

| 任务 | 负责人 | 状态 |
|------|--------|------|
| 创建 `backend/app/parsers/` 目录和 `__init__.py` | Claude | 待实现 |
| 创建 `rawdata_parser.py` 骨架代码 | Claude | 待实现 |
| 创建 `metadata_parser.py` 骨架代码 | Claude | 待实现 |
| **填充 `rawdata_parser.py` 解析逻辑** | **用户** | 待提供 |
| **填充 `metadata_parser.py` 解析逻辑** | **用户** | 待提供 |
| 修改 `parser.py` 服务层 (调用解析、保存 Parquet) | Claude | 待实现 |
| 修改 `trigger_parse` API (阶段 2 入口) | Claude | 待实现 |
| 在上传/导入后调用元数据解析 (阶段 1 入口) | Claude | 待实现 |
| 添加依赖 (pandas, pyarrow) 到 `pyproject.toml` | Claude | 待实现 |

---

## 9. 用户需要准备的代码

### 9.1 `backend/app/parsers/rawdata_parser.py`

```python
"""
原始传感器数据解析器;
解析 .rawdata 文件, 提取各类传感器数据;
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

def get_raw_data(file_path: str, encoding: str = 'utf-8', is_ring: bool = False) -> Dict[str, Any]:
    """
    解析 rawdata 文件, 提取各类传感器数据;
    
    Parameters:
        file_path: rawdata 文件路径 (已解压)
        encoding: 文件编码
        is_ring: 是否为戒指设备
    
    Returns:
        包含各传感器 DataFrame 的字典 (动态 key)
        出错时返回 {"error": "..."}
    """
    try:
        # === 用户解析逻辑 ===
        result = {}
        
        # 示例: 解析加速度数据
        # if acc_data_exists:
        #     result["acc_df"] = pd.DataFrame(...)
        
        return result
    except Exception as e:
        return {"error": str(e)}
```

### 9.2 `backend/app/parsers/metadata_parser.py`

```python
"""
文件元数据解析器;
快速读取文件头部, 提取基本信息;
"""
from typing import Dict, Any

def parse_metadata(file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    快速解析文件头部元数据;
    
    Parameters:
        file_path: rawdata 文件路径 (已解压)
        encoding: 文件编码
    
    Returns:
        元数据字典 (动态 key)
        出错时返回 {"error": "..."}
    """
    try:
        result = {}
        
        # === 用户元数据解析逻辑 ===
        # result["is_ring"] = ...
        # result["data_types"] = [...]
        # result["estimated_duration"] = "00:05:30"
        
        return result
    except Exception as e:
        return {"error": str(e)}
```
