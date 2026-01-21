# SensorHub Analytics

SensorHub Analytics is a dashboard for managing and analyzing sensor data files from wearable devices (Watch and Ring). It provides a unified interface for uploading raw data, monitoring processing status, and inspecting signal quality.

## Features

- **Dashboard**: Real-time overview of file statistics, today's uploads, and storage usage.
- **Quick Upload**: dedicated upload areas for Watch (`.rawdata`) and Ring (`.rawdata`) files with drag-and-drop support.
- **Data Management**: Searchable and filterable table of all sensor files.
  - Filter by Device Type (Watch/Ring) and Status (Idle/Ready/Processing/Failed).
  - Inline editing for notes and test types.
  - Packet inspection popover for quick quality checks.
- **Visual Feedback**: Status badges and signal presence indicators (ACC, PPG, GYRO, etc.).

## Tech Stack

- **Framework**: Vue 3 + Vite + TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide Vue Next

## Run Locally

**Prerequisites:** Node.js

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```
