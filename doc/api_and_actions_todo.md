# Backend API Interfaces & Frontend Actions

This document outlines the required backend API endpoints and corresponding frontend actions based on the current UI implementation of SensorHub.

## 1. System Overview & Statistics
**Component**: `ActionArea` (Right Side Stats)

### 1.1 Fetch System Statistics
- **Description**: Retrieves aggregate metrics for the dashboard.
- **Frontend Trigger**: Page Load / Polling (every 30s).
- **Endpoint**: `GET /api/stats`
- **Response**:
  ```json
  {
    "totalFiles": 12450,
    "processingCount": 5,
    "successRate": 98.2,
    "storageUsed": "450GB",
    "lastUpdated": "2023-10-27T10:00:00Z"
  }
  ```

## 2. File Management
**Component**: `DataTable`

### 2.1 Fetch File List
- **Description**: Retrieves a paginated list of files with filtering and sorting.
- **Frontend Trigger**: Page Load, Filter Change, Page Change, Search Input.
- **Endpoint**: `GET /api/files`
- **Query Parameters**:
  - `page`: number (default 1)
  - `limit`: number (default 10)
  - `search`: string (filename, notes, or id)
  - `device`: string | "All" ("Watch", "Ring")
  - `status`: string | "All" ("Idle", "Ready", "Processing", "Failed")
  - `sort`: string (e.g., "-uploadTime")
- **Response**:
  ```json
  {
    "items": [
      {
        "id": "f_123",
        "status": "Ready",
        "fileName": "sensor_data_2023.raw",
        "uploadTime": "2023-10-27T09:00:00Z",
        "deviceType": "Watch",
        "dataContent": "Accelerometer",
        "testType": "Walk",

        "notes": "Test subject A"
      }
    ],
    "total": 150,
    "page": 1,
    "totalPages": 15
  }
  ```

### 2.2 Update File Metadata
- **Description**: Updates editable fields like Test Type.
- **Frontend Trigger**: Test Type Selection.
- **Endpoint**: `PATCH /api/files/:id`
- **Body**: `{ "testType": "Run" }`

### 2.3 Delete File
- **Description**: Deletes a single file.
- **Frontend Trigger**: Action Menu -> Delete.
- **Endpoint**: `DELETE /api/files/:id`

### 2.4 Batch Delete
- **Description**: Deletes multiple selected files.
- **Frontend Trigger**: Toolbar -> Delete Selected.
- **Endpoint**: `POST /api/files/batch-delete`
- **Body**: `{ "ids": ["f_123", "f_124"] }`

## 3. Upload & Processing
**Components**: `ActionArea` (Quick Upload), `GlobalDragDrop`, `DataTable` (Actions)

### 3.1 Upload Files
- **Description**: Handles file uploads (including drag & drop).
- **Frontend Trigger**: Drop file, Select file.
- **Endpoint**: `POST /api/upload`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (binary), `deviceType` (optional)
- **Response**:
  ```json
  {
    "success": true,
    "fileId": "f_125",
    "message": "Upload complete"
  }
  ```

### 3.2 Start Parsing (Single)
- **Description**: Triggers the parsing/analysis job for a file.
- **Frontend Trigger**: Action Button (Play/Retry).
- **Endpoint**: `POST /api/files/:id/parse`
- **Response**: `{ "jobId": "j_999", "status": "Processing" }`

### 3.3 Batch Parse
- **Description**: Triggers parsing for multiple files.
- **Frontend Trigger**: Toolbar -> Start Parsing.
- **Endpoint**: `POST /api/files/batch-parse`
- **Body**: `{ "ids": ["f_123", "f_124"] }`

### 3.4 Download File
- **Description**: Downloads the original file or parsed report.
- **Frontend Trigger**: Action Menu -> Download.
- **Endpoint**: `GET /api/files/:id/download`

## 4. Analysis Report
**Component**: `DataTable` (Eye Icon)

### 4.1 Get Analysis Report
- **Description**: Fetch detailed analysis results (not full file content).
- **Frontend Trigger**: Click Eye Icon.
- **Endpoint**: `GET /api/files/:id/report`
- **Response**: JSON structure for rendering reports/charts.
