# SensorHub 表结构重构设计文档 (v1.0)

**文档状态**: 已确认 (Confirmed)  
**最后更新**: 2026-02-10  
**关联文档**: `BackendArchitectureDesign(v1.0).md`, `DataStoragProcessingArchitectureDesign(v1.0).md`

---

## 1. 背景与动机

当前 `SensorFile` 表承担了过多职责，包含三类不同性质的字段：

| 类别 | 字段 | 问题 |
|------|------|------|
| **设备信息** | `device_type`, `device_model` | 与 `DeviceMapping` 表重复存储，修改时需同步两处 |
| **解析状态** | `status`, `duration`, `packets`, `error_message`, `progress`, `processed_dir` | 文件完整性状态与解析进度状态混在同一个 `status` 字段 |
| **解析元数据** | `content_meta` | 文件头提取的 metadata 与解析输出信息缺乏清晰归属 |

**目标：** 按单一职责原则将 `SensorFile` 拆分为三张表，每张表只管一件事。

---

## 2. 核心设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | `SensorFile` 只管文件元信息，`DeviceMapping` 只管设备映射，`ParseResult` 只管解析结果 |
| **设备信息只存一处** | `device_type` / `device_model` 只在 `DeviceMapping` 表中，`SensorFile` 通过 `device_name` 关联 |
| **解析状态独立** | 解析的状态、进度、结果全部移入 `ParseResult` 表 |
| **1:1 关系** | 每个 `SensorFile` 最多对应一条 `ParseResult`（可重复解析，但只保留最终结果） |
| **API 兼容** | 后端 JOIN 展平返回，前端接口形状保持不变 |

---

## 3. 重构后表结构

### 3.1 PhysicalFile（不变）

物理存储去重表，与本次重构无关。

```
PhysicalFile
├── hash         PK    MD5/SHA256
├── size               文件大小 (Bytes)
├── path               Zstd 压缩路径
├── created_at         首次入库时间
├── compression_ratio  压缩率
└── frame_index  JSON  帧索引元数据
```

### 3.2 SensorFile（瘦身）

**职责：** 文件身份 + 上传元信息 + 来源设备关联

```
SensorFile
├── id               PK    UUID
├── file_hash        FK    → PhysicalFile.hash
├── device_name      FK    → DeviceMapping.device_name (可为空)
├── filename               原始文件名
├── name_suffix            重复后缀 " (1)"
├── file_size_bytes        文件字节数 (去重用)
├── size                   显示用字符串 "1.2 MB"
├── file_status            unverified | verified | error  ← 原 status 重命名
├── uploaded_by            上传者
├── upload_time            上传时间
├── tester                 测试人员
├── mac                    设备 MAC
├── collection_time        采集时间
├── start_time             开始时间 (from metadata)
├── device_mac             设备 MAC (from metadata)
├── device_version         固件版本 (from metadata)
├── user_name              用户名 (from metadata)
├── timezone               时区 GMT+08:00
├── test_type_l1           一级测试类型
├── test_type_l2           二级测试类型
└── notes                  备注
```

**移除的字段：**

| 字段 | 去向 | 原因 |
|------|------|------|
| `device_type` | `DeviceMapping` | 设备信息只存一处 |
| `device_model` | `DeviceMapping` | 设备信息只存一处 |
| `status` | 重命名为 `file_status` | 仅保留文件级状态，解析状态移入 `ParseResult` |
| `duration` | `ParseResult` | 解析输出 |
| `packets` | `ParseResult` | 解析输出 |
| `error_message` | `ParseResult` | 解析错误信息 |
| `progress` | `ParseResult` | 解析进度 |
| `content_meta` | `ParseResult` | 文件头元数据，解析阶段产出 |
| `processed_dir` | `ParseResult` | 解析产物路径 |

**`file_status` 状态值：**

| 值 | 含义 |
|---|---|
| `unverified` | 刚上传，后台校验中 |
| `verified` | 校验通过，可以解析 |
| `error` | 上传校验失败（hash 不匹配、文件损坏等） |

### 3.3 DeviceMapping（不变）

**职责：** `device_name` → `device_type` + `device_model` 的唯一映射

```
DeviceMapping
├── device_name    PK    设备名称
├── device_type          Watch / Ring
└── device_model         厂商型号 (大写存储)
```

### 3.4 ParseResult（新建）

**职责：** 存储每个文件的解析状态和结果，1:1 对应 `SensorFile`

```
ParseResult
├── id                PK    自增主键
├── sensor_file_id    FK    → SensorFile.id (UNIQUE 约束, 1:1)
├── device_type_used        解析时使用的 device_type 快照
├── status                  idle | processing | processed | error | failing
├── progress          ?     0–100
├── duration                记录时长
├── packets                 JSON 数组 (数据包信息)
├── error_message     ?     错误详情
├── content_meta      JSON  文件头解析出的元数据
├── processed_dir     ?     解析产物目录路径
├── created_at              创建时间
└── updated_at              更新时间
```

**关键设计决策：**

1. **1:1 关系**：`sensor_file_id` 带 UNIQUE 约束。可重复解析，但旧数据会被覆盖（UPDATE），不保留历史。
2. **`device_type_used` 快照**：解析启动时从 `DeviceMapping` 拍快照写入，用于记录该次解析使用的设备类型。
3. **`content_meta` 唯一存放处**：文件头提取的 metadata（startTime、device、packets 等）统一存在此处，便于统一管理和修改。

**`status` 状态值：**

| 值 | 含义 |
|---|---|
| `idle` | 等待解析（新创建或设备类型变更后重置） |
| `processing` | 解析进行中 |
| `processed` | 解析完成 |
| `error` | 解析失败 |
| `failing` | 部分失败 |

---

## 4. 表关系

```
PhysicalFile  1 ──── N  SensorFile
DeviceMapping 1 ──── N  SensorFile    (通过 device_name)
SensorFile    1 ──── 1  ParseResult   (通过 sensor_file_id UNIQUE)
```

---

## 5. 状态生命周期

### 5.1 文件状态 (`SensorFile.file_status`)

```
上传完成 → [unverified]
              │
         后台校验通过 → [verified]
              │
         校验失败 → [error]
              │
         重新上传 → [unverified]
```

> 文件状态只关心文件完整性，与解析无关。

### 5.2 解析状态 (`ParseResult.status`)

```
文件 verified 后创建 → [idle]
                         │
                    触发解析 → [processing]
                         │
              ┌──────────┼──────────┐
          解析成功     解析失败     部分失败
              │          │          │
         [processed]  [error]  [failing]
              │          │          │
              └──────────┴──────────┘
                         │
              device_type 变更 → [idle]  (已处理的重置为 idle)
                         │
                      重试 → [processing]
```

> **重要**：设备类型变更时，只有 `status = "processed"` 的 `ParseResult` 会被重置为 `idle`。前端更新设备类型时应提示用户"将导致已解析的文件需重新解析"。

---

## 6. 关键流程

### 6.1 上传流程

```
1. 用户上传文件
2. 创建 SensorFile (file_status = "unverified")
3. 后台 verify_upload_task 启动
4. 校验通过 → file_status = "verified"
5. 创建 ParseResult (status = "idle", device_type_used = DeviceMapping 当前值)
6. 将文件头 metadata 解析结果写入 ParseResult.content_meta
```

### 6.2 解析流程

```
1. 用户触发解析(或自动触发)
2. 查找 SensorFile 对应的 ParseResult
3. 确认 file_status = "verified" 且 ParseResult.status = "idle"
4. 从 DeviceMapping 获取当前 device_type，写入 device_type_used
5. ParseResult.status = "processing", progress = 0
6. 执行解析…
7a. 成功 → status = "processed", 写入 duration/packets/content_meta/processed_dir
7b. 失败 → status = "error", 写入 error_message
7c. 部分失败 → status = "failing"
```

### 6.3 设备类型变更级联

```
1. DeviceMapping.device_type 发生变更
2. 查找所有 device_name 匹配的 SensorFile
3. 对每个 SensorFile 的 ParseResult:
   - 如果 status = "processed" → 重置为 "idle"
   - 其他状态不变
4. 前端收到更新后刷新列表，显示这些文件需重新解析
```

> **前端注意事项**：修改设备类型时应弹出确认对话框，提示"修改设备类型会导致 N 个已解析的文件需重新解析，是否继续？"

---

## 7. API 响应兼容策略

后端返回 `SensorFileResponse` 时做 JOIN 展平，**前端 `SensorFile` 接口不需要修改**：

```python
# API 返回格式 (保持不变):
{
    "id": "uuid-xxx",
    "filename": "HeartRate_Daylife.rawdata",
    "deviceType": "Watch",          # ← JOIN DeviceMapping.device_type
    "deviceModel": "CHR03",         # ← JOIN DeviceMapping.device_model  
    "deviceName": "VITA RING S2",   # ← SensorFile.device_name
    "status": "processed",          # ← ParseResult.status (若无 ParseResult 则取 file_status)
    "duration": "01:23:45",         # ← ParseResult.duration
    "packets": [...],               # ← ParseResult.packets
    "progress": 100,                # ← ParseResult.progress
    "errorMessage": null,           # ← ParseResult.error_message
    "contentMeta": {...},           # ← ParseResult.content_meta
    "processedDir": "storage/...",  # ← ParseResult.processed_dir
    "size": "1.2 MB",
    "uploadTime": "2026-02-10T...",
    ...
}
```

**状态合并逻辑**：

```python
def get_display_status(file: SensorFile, parse_result: Optional[ParseResult]) -> str:
    if parse_result:
        return parse_result.status
    # 无 ParseResult 时，映射 file_status
    if file.file_status == "verified":
        return "idle"  # verified 但未创建 ParseResult → 显示为 idle
    return file.file_status  # unverified / error 原样返回
```

---

## 8. 数据迁移策略

对现有数据库执行以下迁移：

### 8.1 步骤

```sql
-- Step 1: 创建 parse_results 表
CREATE TABLE parse_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_file_id TEXT NOT NULL UNIQUE,
    device_type_used TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'idle',
    progress INTEGER,
    duration TEXT NOT NULL DEFAULT '--',
    packets TEXT NOT NULL DEFAULT '[]',
    error_message TEXT,
    content_meta JSON,
    processed_dir TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_file_id) REFERENCES sensor_files(id)
);

-- Step 2: 迁移现有数据 (status 不是 unverified 的)
INSERT INTO parse_results (sensor_file_id, device_type_used, status, duration, packets,
                           error_message, content_meta, processed_dir, progress)
SELECT id, device_type,
       CASE WHEN status IN ('idle','processing','processed','error','failing') THEN status
            ELSE 'idle' END,
       duration, packets, error_message, content_meta, processed_dir, progress
FROM sensor_files
WHERE status != 'unverified';

-- Step 3: 重命名 status → file_status 并映射值
-- SQLite 不支持 RENAME COLUMN + 默认值变更，需重建表
-- 映射: unverified → unverified
--        idle/processing/processed/error/failing → verified
--        error (上传错误) → error  (需根据 error_message 判断)

-- Step 4: 删除 SensorFile 上的废弃列
-- device_type, device_model, duration, packets, error_message, progress,
-- content_meta, processed_dir
-- (SQLite 需 CREATE TABLE AS + DROP + RENAME 方式)
```

### 8.2 file_status 迁移映射

| 原 `status` 值 | 新 `file_status` 值 | 说明 |
|---|---|---|
| `unverified` | `unverified` | 保持不变 |
| `idle` | `verified` | 已通过校验 |
| `processing` | `verified` | 正在解析 = 已通过校验 |
| `processed` | `verified` | 解析完成 = 已通过校验 |
| `error` (解析错误) | `verified` | 解析失败但文件本身正常 |
| `failing` | `verified` | 部分失败但文件本身正常 |
| `error` (上传错误) | `error` | 文件校验失败 |

> **注意**：区分"上传错误"和"解析错误"需要检查 `error_message` 内容或是否存在 `ParseResult`。保守策略：所有有 `ParseResult` 迁移记录的都标记为 `verified`。

---

## 9. 影响范围

### 9.1 后端

| 文件 | 变更内容 |
|------|----------|
| `models/sensor_file.py` | 删除迁移字段，`status` → `file_status`，添加 `parse_result` 关系 |
| **新建** `models/parse_result.py` | `ParseResult` 模型定义 |
| `models/__init__.py` | 导出 `ParseResult` |
| `crud/file.py` | 查询时 LEFT JOIN `ParseResult` + `DeviceMapping`，更新逻辑拆分 |
| **新建** `crud/parse_result.py` | ParseResult CRUD（创建/更新/按 file_id 查询） |
| `crud/device_mapping.py` | `cascade_mapping_to_files` 改为操作 `ParseResult.status` |
| `schemas/api_models.py` | `SensorFileResponse` 改从 JOIN 结果取值，字段来源注释更新 |
| `services/file_service.py` | `verify_upload_task` 创建 `ParseResult`，写入 `content_meta` |
| `services/parser.py` | 解析结果写入 `ParseResult` 而非 `SensorFile` |
| `services/device_import.py` | 创建文件时同步创建 `ParseResult` |
| `api/v1/endpoints/files.py` | PATCH/parse 端点适配新结构 |
| `api/v1/endpoints/device_mappings.py` | 级联逻辑适配 `ParseResult` |

### 9.2 前端

| 文件 | 变更内容 |
|------|----------|
| `types.ts` | **不变** — API 返回格式保持兼容 |
| `stores/fileStore.ts` | **最小改动** — 可能需调整状态检查逻辑 |
| `components/StatusBadge.vue` | **不变** — 状态值名称一致 |
| `components/DataTable.vue` | 设备类型修改时增加确认提示 |
| `components/EditableDeviceCell.vue` | 设备类型修改时增加确认提示 |

---

## 10. 前端注意事项

### 10.1 设备类型修改确认

当用户在前端修改设备类型 (`device_type`) 时，应弹出确认对话框：

```
⚠ 修改设备类型
修改设备类型会导致 N 个已解析的文件需要重新解析。
是否继续？
[取消] [确认修改]
```

后端 API 应在响应中返回受影响的文件数量，供前端展示。

### 10.2 状态显示逻辑

前端无需区分 `file_status` 和 `ParseResult.status`，后端 API 已做合并：

- 有 `ParseResult` → 显示 `ParseResult.status`
- 无 `ParseResult` 且 `file_status = "verified"` → 显示 `"idle"`
- 无 `ParseResult` → 显示 `file_status` 原值

---

## 11. 实施顺序

```
Phase 1: 后端模型层
  1.1 创建 ParseResult 模型
  1.2 修改 SensorFile 模型 (删字段, status → file_status)
  1.3 更新 __init__.py 导出

Phase 2: 数据迁移
  2.1 编写迁移脚本 (创建表 + 数据搬迁)
  2.2 测试迁移 (备份 → 迁移 → 验证)

Phase 3: 后端 CRUD/Service 层
  3.1 创建 ParseResult CRUD
  3.2 修改 file CRUD (JOIN 查询)
  3.3 修改 file_service.py (verify → 创建 ParseResult)
  3.4 修改 device_mapping CRUD (级联操作 ParseResult)
  3.5 修改 parser.py (写入 ParseResult)
  3.6 修改 device_import.py (同步创建 ParseResult)

Phase 4: 后端 API 层
  4.1 修改 SensorFileResponse schema (JOIN 取值)
  4.2 修改 files.py 端点
  4.3 修改 device_mappings.py 端点

Phase 5: 前端适配
  5.1 设备类型修改增加确认提示
  5.2 验证所有状态显示正确
  5.3 端到端测试
```

erDiagram
    PhysicalFile {
        string hash PK "MD5/SHA256"
        int size "文件大小 Bytes"
        string path "Zstd 压缩路径"
        datetime created_at
        string compression_ratio
        json frame_index "帧索引"
    }

    SensorFile {
        string id PK "UUID"
        string file_hash FK "→ PhysicalFile"
        string device_name FK "→ DeviceMapping"
        string filename "原始文件名"
        string name_suffix "重复后缀"
        int file_size_bytes "去重用"
        string size "显示用 1.2MB"
        string file_status "unverified | verified | error"
        string uploaded_by "上传者"
        string upload_time "上传时间"
        string tester "测试人员"
        string start_time "开始时间"
        string device_mac "设备MAC"
        string device_version "固件版本"
        string user_name "用户名"
        string timezone "GMT+08:00"
        string test_type_l1 "一级测试类型"
        string test_type_l2 "二级测试类型"
        string notes "备注"
    }

    DeviceMapping {
        string device_name PK "设备名称"
        string device_type "Watch / Ring"
        string device_model "厂商型号 大写"
    }

    ParseResult {
        int id PK "自增主键"
        string sensor_file_id FK "→ SensorFile UNIQUE 1:1"
        string device_type_used "解析时device_type快照"
        string status "idle|processing|processed|error|failing"
        int progress "0-100"
        string duration "记录时长"
        string packets "JSON数组"
        string error_message "错误信息"
        json content_meta "文件头metadata 唯一存放处"
        string processed_dir "处理后目录路径"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    PhysicalFile ||--o{ SensorFile : "1:N hash去重"
    DeviceMapping ||--o{ SensorFile : "1:N device_name映射"
    SensorFile ||--o| ParseResult : "1:1 UNIQUE约束"
