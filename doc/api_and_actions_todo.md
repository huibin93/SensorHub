# API Interfaces & Frontend Actions TODO List

This document outlines the required backend API endpoints and corresponding frontend actions based on the current UI implementation of SensorHub.

## 1. File Management (DataTable)

### 1.1 Data Fetching
- **Action**: Load the file list when the page mounts or filters/pagination change.
- **Frontend Trigger**: `onMounted`, Pagination clicks, Filter changes (Device/Status).
- **Required API**:
  - `GET /api/files`
  - **Query Parameters**:
    - `page` (number): Current page number.
    - `limit` (number): Items per page (20/50/100).
    - `search` (string): Search query (filename, notes, ID).
    - `device` (string): Filter by device type (All/Watch/Ring).
    - `status` (string): Filter by status (Idle/Processing/Ready/Failed).
  - **Response**: `{ items: SensorFile[], total: number, page: number, totalPages: number }`

### 1.2 Single File Actions
- **Delete File**
  - **Action**: Click "Delete" in the "More" menu.
  - **Required API**: `DELETE /api/files/:id`
- **Download File**
  - **Action**: Click "Download" icon or "Download Raw Data" in menu.
  - **Required API**: `GET /api/files/:id/download` (Should return file blob or redirect to URL).
- **Update Metadata (Notes, Rating, Test Type)**
  - **Action**: Edit Note input, Click Star, or Edit Test Type.
  - **Required API**: `PATCH /api/files/:id`
  - **Body**: `{ notes?: string, rating?: number, testType?: { l1: string, l2: string } }`

### 1.3 Batch Actions
- **Batch Delete**
  - **Action**: Select multiple rows -> Click "Delete" in toolbar.
  - **Required API**: `POST /api/files/batch-delete`
  - **Body**: `{ ids: string[] }`
- **Batch Download**
  - **Action**: Select multiple rows -> Click "Download" in toolbar.
  - **Required API**: `POST /api/files/batch-download` (Likely returns a ZIP archive).
  - **Body**: `{ ids: string[] }`

## 2. Processing / Parsing

### 2.1 Trigger Parsing
- **Action**: Click "Play" (Start) or "Retry" icon on a single row, or "Parse" in batch toolbar.
- **Required API**: `POST /api/processing/start`
- **Body**: `{ ids: string[] }`
- **Response**: List of job IDs or updated file statuses.

### 2.2 Analysis
- **Action**: Click "Eye" (Analyze) icon.
- **Required API**: `GET /api/analysis/:id` (Navigate to analysis page or fetch analysis data).

## 3. Upload (ActionArea)

### 3.1 File Upload
- **Action**: Drag & drop files or click "Upload Data Files".
- **Required API**: `POST /api/upload`
- **Content-Type**: `multipart/form-data`
- **Body**: File object(s).
- **Behavior**: Should support progress tracking and multiple file uploads.

## 4. Statistics (Dashboard)

### 4.1 Stats Summary
- **Action**: Load dashboard statistics.
- **Required API**: `GET /api/stats`
- **Response**: `{ totalFiles: number, todayUploads: number, pendingTasks: number, storageUsed: string }`

## 5. Summary of Frontend Events to Implement

| Component | Event / trigger | Proposed Function Name |
|-----------|------------------|------------------------|
| **DataTable** | Page Mount | `fetchData()` |
| | Search Input | `debouncedSearch()` |
| | Filter Select Change | `fetchData()` (with new params) |
| | Pagination Click | `setPage()` & `fetchData()` |
| | Select All Checkbox | `toggleAllSelection()` |
| | Row Checkbox | `toggleRowSelection()` |
| | **Batch Delete Click** | `handleBatchDelete()` -> Call API -> Refresh List |
| | **Batch Download Click** | `handleBatchDownload()` -> Call API |
| | **Batch Parse Click** | `triggerParse(ids)` -> Call API -> Polling/Socket for updates |
| | Row "Play"/"Retry" | `triggerParse([id])` |
| | Row "Delete" | `deleteFile(id)` |
| | Row "Download" | `downloadFile(id)` |
| | Row Note Blur/Enter | `updateFileMetadata(id, { notes })` |
| | Row Rating Click | `updateFileMetadata(id, { rating })` |
| **ActionArea**| File Drop/Select | `handleFileUpload(files)` |

