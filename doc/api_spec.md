# SensorHub API 规格文档

> **版本**: 1.0.0  
> **更新日期**: 2026-01-25  
> **后端框架**: FastAPI  
> **前端框架**: Vue 3 + Pinia + Axios

---

## 📊 文档概览

本文档包含 SensorHub 系统所有 API 端点的完整规格,并对照 UI 需求进行了查漏补缺分析;

### 实现状态图例
| 标记 | 含义 |
|------|------|
| ✅ | 后端 + 前端均已实现 |
| 🔨 | 后端已实现,前端未对接 |
| ⚠️ | 前端有需求,后端未实现 |
| 📋 | 规划中,尚未实现 |

---

## 1. 统计概览接口 (Statistics/Summary)

### 📍 UI 需求
页面右上角 **SYSTEM OVERVIEW** 区域需要展示：
- Total Files (总文件数): 1,251
- Today (今日新增): 33
- Pending (待处理): 6
- Storage (存储占用): 450 GB
- Updated (更新时间戳): "Just now"

### 1.1 ⚠️ GET `/api/stats` — 获取系统统计
**状态**: 后端未实现,前端使用 Mock 数据

**前端当前实现**:
```typescript
// fileStore.ts - 从本地计算 stats,部分使用硬编码
const stats = computed(() => ({
    totalFiles: files.value.length,      // ✅ 从文件列表计算
    todayUploads: MOCK_STATS.todayUploads, // ⚠️ 硬编码 Mock
    pendingTasks: files.value.filter(...), // ✅ 从文件列表计算
    storageUsed: MOCK_STATS.storageUsed,   // ⚠️ 硬编码 Mock
}));
```

**建议后端实现**:
```http
GET /api/stats
```

**响应体**:
```json
{
  "totalFiles": 1251,
  "todayUploads": 33,
  "pendingTasks": 6,
  "storageUsed": "450 GB",
  "lastUpdated": "2026-01-25T01:00:00Z"
}
```

**更新频率**: 页面加载时获取,可选轮询 (30s-60s)

---

## 2. 核心文件列表接口 (Core File List)

### 📍 UI 需求
**Recent Data Files** 表格需要：
- 分页显示 (20/50/100 items per page)
- 搜索 (filename, notes, ID)
- 筛选 (Device: All/Watch/Ring, Status: All/Idle/Ready/Processing/Failed)
- 排序

### 2.1 🔨 GET `/api/files` — 获取文件列表
**状态**: 后端基础实现,但缺少分页/筛选/搜索功能

**后端当前实现** (main.py):
```python
@app.get("/api/files", response_model=List[SensorFile])
def get_files():
    files = database.get_all_files()
    return files  # ⚠️ 返回全部,无分页
```

**前端当前实现** (fileService.ts):
```typescript
async getFiles(): Promise<SensorFile[]> {
    const response = await axios.get(`${API_BASE_URL}/files`);
    return response.data;  // ⚠️ 无分页参数
}
```

**建议增强**:
```http
GET /api/files?page=1&limit=20&search=watch&device=Watch&status=Ready&sort=-uploadTime
```

**请求参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页条数 (20/50/100) |
| `search` | string | - | 搜索关键词 (filename, notes, id) |
| `device` | string | "All" | 设备筛选 (All/Watch/Ring) |
| `status` | string | "All" | 状态筛选 (All/Idle/Ready/Processing/Failed) |
| `sort` | string | "-uploadTime" | 排序字段,`-` 前缀表示降序 |

**响应体** (建议增强):
```json
{
  "items": [
    {
      "id": "f_001",
      "filename": "watch_run_001.raw",
      "status": "Ready",
      "size": "256 MB",
      "duration": "01:30:00",
      "uploadTime": "2023-10-27T10:30:00Z",
      "deviceType": "Watch",
      "deviceModel": "Watch S8",
      "testTypeL1": "Run",
      "testTypeL2": "Outdoor",
      "notes": "Test for dropped frames",
      "packets": [
        {"name": "ACC", "freq": "100Hz", "count": 10000, "present": true}
      ],
      "errorMessage": null,
      "progress": null
    }
  ],
  "total": 1251,
  "page": 1,
  "limit": 20,
  "totalPages": 63
}
```

---

### 2.2 ✅ GET `/api/files/{id}` — 获取单个文件
**状态**: 后端已实现

```http
GET /api/files/f_001
```

**响应体**: 单个 `SensorFile` 对象

---

### 2.3 ✅ PATCH `/api/files/{id}` — 更新文件元数据
**状态**: 后端已实现,前端 Store 有乐观更新但未调用 API

**后端实现** (main.py):
```python
@app.patch("/api/files/{file_id}", response_model=SensorFile)
def update_file(file_id: str, request: FileUpdateRequest):
    # 支持部分更新
```

**前端当前实现** (fileStore.ts):
```typescript
async function updateNote(id: string, note: string) {
    const file = files.value.find(f => f.id === id);
    if (file) {
        file.notes = note;  // ✅ 乐观更新
        // TODO: In Phase 4, call fileService.updateFile(id, { notes: note })
        // ⚠️ 未调用后端 API
    }
}
```

**请求体** (支持部分更新):
```json
{
  "notes": "Updated note",
  "deviceType": "Watch",
  "deviceModel": "Apple Watch Series 9",
  "testTypeL1": "Run",
  "testTypeL2": "Outdoor",
  "status": "Ready"
}
```

**需要修复**: 前端 Store 中的 `updateNote`, `updateDevice`, `updateTestType` 函数需要调用 `fileService.updateFile()`

---

### 2.4 ✅ DELETE `/api/files/{id}` — 删除单个文件
**状态**: 后端已实现,前端仅本地删除未调用 API

```http
DELETE /api/files/f_001
```

**响应体**:
```json
{"status": "deleted", "id": "f_001"}
```

---

### 2.5 ✅ POST `/api/files/batch-delete` — 批量删除
**状态**: 后端已实现,前端仅本地删除未调用 API

```http
POST /api/files/batch-delete
Content-Type: application/json

{"ids": ["f_001", "f_002", "f_003"]}
```

**响应体**:
```json
{"status": "deleted", "count": 3}
```

---

## 3. 配置与字典数据接口 (Metadata/Dictionaries)

### 📍 UI 需求
筛选下拉框和编辑器需要预加载的选项数据：
- 设备类型列表 (Watch, Ring)
- 设备型号列表 (Apple Watch Series 9, Oura Ring Gen 3, ...)
- 测试类型树 (L1: Run, Walk, Sleep → L2: Outdoor, Indoor, ...)
- 状态列表 (Idle, Ready, Processing, Failed)

### 3.1 ⚠️ GET `/api/devices` — 获取设备字典
**状态**: 后端未实现,前端硬编码

**前端当前实现** (deviceStore.ts):
```typescript
// 硬编码的设备型号列表
export const deviceModels = ref<Record<DeviceType, string[]>>({
    [DeviceType.Watch]: [
        'Apple Watch Series 9',
        'Samsung Galaxy Watch 6',
        // ...
    ],
    [DeviceType.Ring]: [
        'Oura Ring Gen 3',
        // ...
    ]
});
```

**建议后端实现**:
```http
GET /api/devices
```

**响应体**:
```json
{
  "deviceTypes": [
    {"type": "Watch", "label": "Smart Watch"},
    {"type": "Ring", "label": "Smart Ring"}
  ],
  "deviceModels": {
    "Watch": ["Apple Watch Series 9", "Samsung Galaxy Watch 6", "Fitbit Sense 2"],
    "Ring": ["Oura Ring Gen 3", "Samsung Galaxy Ring", "Ultrahuman Ring AIR"]
  }
}
```

---

### 3.2 ⚠️ GET `/api/test-types` — 获取测试类型树
**状态**: 后端未实现,前端硬编码

**前端当前实现** (testTypeStore.ts):
```typescript
export const testTypesL1 = ref<string[]>(['Unknown', 'Run', 'Walk', 'Sleep', ...]);
export const testTypesL2 = ref<Record<string, string[]>>({
    'Run': ['Outdoor', 'Indoor', 'Treadmill'],
    // ...
});
```

**建议后端实现**:
```http
GET /api/test-types
```

**响应体**:
```json
{
  "types": [
    {
      "id": "run",
      "name": "Run",
      "subTypes": ["Outdoor", "Indoor", "Treadmill"]
    },
    {
      "id": "walk",
      "name": "Walk",
      "subTypes": ["Outdoor", "Indoor"]
    },
    {
      "id": "sleep",
      "name": "Sleep",
      "subTypes": ["Night Rest", "Nap"]
    }
  ]
}
```

---

### 3.3 ⚠️ POST `/api/devices/models` — 添加新设备型号
**状态**: 后端未实现,前端仅本地添加

```http
POST /api/devices/models
Content-Type: application/json

{
  "deviceType": "Watch",
  "modelName": "Garmin Fenix 8"
}
```

---

### 3.4 ⚠️ POST `/api/test-types` — 添加新测试类型
**状态**: 后端未实现,前端仅本地添加

```http
POST /api/test-types
Content-Type: application/json

{
  "name": "Swimming",
  "subTypes": ["Pool", "Open Water"]
}
```

---

### 3.5 ⚠️ POST `/api/test-types/{typeId}/sub-types` — 添加子类型
**状态**: 后端未实现

```http
POST /api/test-types/run/sub-types
Content-Type: application/json

{"name": "Trail"}
```

---

## 4. 文件上传接口 (File Upload)

### 📍 UI 需求
**Quick Upload** 区域支持：
- 拖拽上传
- 点击选择上传
- 支持 `.rawdata` 和 `.zip` 格式
- 实时上传进度显示

### 4.1 ⚠️ POST `/api/upload` — 文件上传
**状态**: 后端未实现

```http
POST /api/upload
Content-Type: multipart/form-data

file: <binary>
deviceType: Watch (optional)
```

**响应体**:
```json
{
  "success": true,
  "fileId": "f_125",
  "filename": "watch_run_002.raw",
  "message": "Upload complete"
}
```

**上传进度**: 通过 Axios `onUploadProgress` 回调或 WebSocket 实现

---

### 4.2 📋 GET `/api/upload/config` — 获取上传配置
**状态**: 规划中

```http
GET /api/upload/config
```

**响应体**:
```json
{
  "allowedExtensions": [".rawdata", ".zip"],
  "maxFileSize": "500MB",
  "maxConcurrentUploads": 3
}
```

---

## 5. 解析处理接口 (Parsing/Processing)

### 📍 UI 需求
- 表格 Actions 列的 Play/Retry 按钮触发单文件解析
- 工具栏批量 Parse 按钮触发多文件解析
- 解析进度显示 (0-100%)

### 5.1 ⚠️ POST `/api/files/{id}/parse` — 触发单文件解析
**状态**: 后端未实现,前端模拟进度

**前端当前实现** (fileStore.ts):
```typescript
function triggerParse(ids: string[]) {
    // 本地模拟进度,无后端调用
    ids.forEach(id => {
        file.status = FileStatus.Processing;
        file.progress = 0;
    });
    // setInterval 模拟进度增长...
}
```

**建议后端实现**:
```http
POST /api/files/f_001/parse
```

**响应体**:
```json
{
  "jobId": "job_123",
  "fileId": "f_001",
  "status": "Processing",
  "estimatedTime": "30s"
}
```

---

### 5.2 ⚠️ POST `/api/files/batch-parse` — 批量解析
**状态**: 后端未实现

```http
POST /api/files/batch-parse
Content-Type: application/json

{"ids": ["f_001", "f_002", "f_003"]}
```

**响应体**:
```json
{
  "jobs": [
    {"jobId": "job_123", "fileId": "f_001", "status": "Processing"},
    {"jobId": "job_124", "fileId": "f_002", "status": "Processing"}
  ]
}
```

---

### 5.3 📋 GET `/api/jobs/{jobId}` — 查询任务状态
**状态**: 规划中 (或用 WebSocket 推送)

```http
GET /api/jobs/job_123
```

**响应体**:
```json
{
  "jobId": "job_123",
  "fileId": "f_001",
  "status": "Processing",
  "progress": 65,
  "startedAt": "2026-01-25T01:00:00Z"
}
```

---

## 6. 下载接口 (Download)

### 6.1 ⚠️ GET `/api/files/{id}/download` — 下载原始文件
**状态**: 后端未实现

```http
GET /api/files/f_001/download
```

**响应**: 文件流 (Content-Disposition: attachment)

---

### 6.2 📋 POST `/api/files/batch-download` — 批量下载 (打包ZIP)
**状态**: 规划中

```http
POST /api/files/batch-download
Content-Type: application/json

{"ids": ["f_001", "f_002"]}
```

---

## 7. 分析报告接口 (Analysis Report)

### 📍 UI 需求
表格 Actions 列的 Eye 图标 (Analyze 按钮) 查看分析结果

### 7.1 📋 GET `/api/files/{id}/report` — 获取分析报告
**状态**: 规划中

```http
GET /api/files/f_001/report
```

**响应体**:
```json
{
  "fileId": "f_001",
  "summary": {
    "duration": "01:30:00",
    "dataQuality": "Good",
    "anomalies": 2
  },
  "packets": [
    {"name": "ACC", "freq": "100Hz", "count": 540000, "quality": 99.2},
    {"name": "PPG", "freq": "25Hz", "count": 135000, "quality": 97.8}
  ],
  "charts": {
    "heartRate": [...],
    "activity": [...]
  }
}
```

---

## 8. 用户与权限接口 (User/Session)

### 📍 UI 需求
- 左下角用户头像/缩写 (JD)
- 权限控制 (编辑/删除按钮可见性)

### 8.1 📋 GET `/api/user/me` — 获取当前用户
**状态**: 规划中

```http
GET /api/user/me
Authorization: Bearer <token>
```

**响应体**:
```json
{
  "id": "u_001",
  "name": "Jane Doe",
  "initials": "JD",
  "email": "jane@example.com",
  "permissions": ["file:read", "file:write", "file:delete"]
}
```

---

## 📊 GAP Analysis 汇总

### 已实现 ✅
| 接口 | 后端 | 前端调用 |
|------|------|----------|
| GET /api/files | ✅ | ✅ |
| GET /api/files/{id} | ✅ | ❌ |
| PATCH /api/files/{id} | ✅ | ❌ (有TODO) |
| DELETE /api/files/{id} | ✅ | ❌ |
| POST /api/files/batch-delete | ✅ | ❌ |

### 需要实现 ⚠️
| 优先级 | 接口 | 说明 |
|--------|------|------|
| **P0** | GET /api/stats | System Overview 需要 |
| **P0** | GET /api/files (分页) | 列表性能优化必需 |
| **P0** | POST /api/upload | 核心上传功能 |
| **P1** | GET /api/devices | 设备字典持久化 |
| **P1** | GET /api/test-types | 测试类型持久化 |
| **P1** | POST /api/files/{id}/parse | 解析触发 |
| **P2** | GET /api/files/{id}/download | 文件下载 |
| **P2** | GET /api/files/{id}/report | 分析报告展示 |
| **P3** | GET /api/user/me | 用户认证 |

### 前端需要补充的调用
1. `fileStore.updateNote()` → 调用 `fileService.updateFile()`
2. `fileStore.updateDevice()` → 调用 `fileService.updateFile()`
3. `fileStore.updateTestType()` → 调用 `fileService.updateFile()`
4. `fileStore.deleteFile()` → 调用 `fileService.deleteFile()`
5. `fileStore.deleteFiles()` → 调用 `fileService.deleteFiles()`

---

## 🔧 下一步建议

1. **Phase 1**: 完成前端与现有后端 API 的对接 (PATCH/DELETE)
2. **Phase 2**: 实现 `/api/stats` 和分页版 `/api/files`
3. **Phase 3**: 实现文件上传 `/api/upload`
4. **Phase 4**: 实现配置字典接口 (`/api/devices`, `/api/test-types`)
5. **Phase 5**: 实现解析和下载功能
